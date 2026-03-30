import tempfile
import sys

from pathlib import Path
from subprocess import PIPE, Popen
from typing import Optional

from dgis.hooks.plugins.plugin import Plugin, PluginContext, PluginResult, PluginResultPayload, PluginResultStatus
from dgis.hooks.utility.format import is_supported_cpp_file_extension
from dgis.hooks.utility.env import setup_env


class ClangFormatCheckPlugin(Plugin):
    @classmethod
    def _find_clang_format_style(cls, context: PluginContext) -> Optional[str]:
        clang_format_style = None
        for obj in context.repo.tree("HEAD").traverse():
            if obj.type == "blob" and obj.name == ".clang-format":
                clang_format_style = obj.hexsha
                break
        return clang_format_style

    @classmethod
    def execute(cls, context: PluginContext) -> PluginResult:
        payloads = None

        binary_path = "clang-format"

        script_cmd = [sys.executable, "-m", "dgis.hooks.scripts.clang_format_diff"]

        # Prepare environment for subprocess so that the child python process
        # can import the local `dgis` package when tests run without package install.
        env = setup_env()

        with tempfile.TemporaryDirectory() as tmp_dir:
            if context.log:
                context.log.debug(f"Running in temp dir: '{tmp_dir}'")

            clang_format_style = cls._find_clang_format_style(context)
            if clang_format_style:
                if context.log:
                    context.log.debug(f"Found .clang-format HEXSHA: '{clang_format_style}'")
                with open(Path(tmp_dir) / ".clang-format", "wb") as file:
                    file.write(context.repo.git.cat_file("blob", clang_format_style).encode())
            else:
                if context.log:
                    context.log.warning(f"No clang-format style file found while executing '{cls.__name__}'")
                return PluginResult(PluginResultStatus.Ok, None)

            diff = context.ref.diff(context.repo)
            for diff_content in diff:
                if diff_content.deleted_file:
                    continue

                if diff_content.renamed_file and not diff_content.b_blob:
                    continue

                file_path = Path(tmp_dir) / diff_content.b_path
                if is_supported_cpp_file_extension(file_path.suffix):
                    if len(file_path.parents) > 0 and not file_path.parent.exists():
                        file_path.parent.mkdir(parents=True)
                    with open(file_path, "wb") as file:
                        file.write(context.repo.git.cat_file("blob", diff_content.b_blob.hexsha).encode())
                else:
                    continue

                if context.log:
                    context.log.debug(f"Executing '{cls.__name__}' for file: '{file_path}'")

                diff_file_path = file_path.with_suffix(".diff")
                with open(diff_file_path, "bw") as file:
                    if not isinstance(diff_content.diff, (bytearray, bytes)):
                        binary_diff = diff_content.diff.encode()
                    else:
                        binary_diff = diff_content.diff
                    file.write(binary_diff)

                clang_format_call = script_cmd + [
                    "-style=file",
                    f"-filesrc={file_path.absolute()}",
                    f"-filediff={diff_file_path.absolute()}",
                    f"-binary={binary_path}",
                    f"-workdir={Path(tmp_dir).absolute()}",
                ]

                if context.log:
                    context.log.debug(f"Calling clang-format tool: {' '.join(map(str, clang_format_call))}")

                p = Popen(clang_format_call, stdin=PIPE, stdout=PIPE, stderr=PIPE, env=env)
                out, err = p.communicate()
                if p.returncode != 0:
                    if not payloads:
                        payloads = [
                            PluginResultPayload(
                                stdout=out.decode(), stderr=err.decode(), diff=out.decode(), file=file_path
                            )
                        ]
                    else:
                        payloads.append(
                            PluginResultPayload(
                                stdout=out.decode(), stderr=err.decode(), diff=out.decode(), file=file_path
                            )
                        )

        if not payloads:
            return PluginResult(PluginResultStatus.Ok, None)

        return PluginResult(PluginResultStatus.Failed, payloads)

    @classmethod
    def post_execute(cls, context: PluginContext, result: PluginResult):
        if not context.log:
            return

        log_func = context.log.info if result.status == PluginResultStatus.Ok else context.log.error
        log_func(f"Check '{cls.__name__}' finished with status: '{result.status}'")

        if result.status == PluginResultStatus.Ok:
            return

        if result.payloads:
            for payload in result.payloads:
                context.log.error(f"Check formatting failed for file: '{payload.file}'")
                if payload.stdout:
                    context.log.error(f"With stdout:\n{payload.stdout}")
                if payload.stderr:
                    context.log.error(f"With stderr:\n{payload.stderr}")
