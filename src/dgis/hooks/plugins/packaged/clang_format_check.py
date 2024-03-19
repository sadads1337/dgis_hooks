import tempfile

from pathlib import Path
from subprocess import PIPE, Popen
from typing import Optional

from dgis.hooks.plugins.plugin import Plugin, PluginContext, PluginResult, PluginResultStatus


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
        errors = {}

        binary_path = "clang-format"

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

                file_path = Path(tmp_dir) / diff_content.b_path
                if file_path.suffix in [".cpp", ".c", ".h", ".hpp", ".hqt"]:
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
                    if diff_content.a_blob and diff_content.b_blob:
                        binary_diff = context.repo.git.diff("-U0", diff_content.a_blob.hexsha,
                                                            diff_content.b_blob.hexsha).encode()
                    elif not diff_content.a_blob and diff_content.b_blob:
                        binary_diff = context.repo.git.diff("--no-index", "--", "/dev/null", file_path.absolute(),
                                                            with_exceptions=False).encode()
                    file.write(binary_diff)

                clang_format_call = [
                    "dgis-clang-format-diff",
                    "-style=file",
                    f"-filesrc={file_path.absolute()}",
                    f"-filediff={diff_file_path.absolute()}",
                    f"-binary={binary_path}",
                    f"-workdir={Path(tmp_dir).absolute()}",
                ]

                p = Popen(clang_format_call, stdin=PIPE, stdout=PIPE, stderr=PIPE)
                out, err = p.communicate()
                if p.returncode != 0:
                    errors[file_path] = (out.decode(), err.decode())

        return PluginResult(PluginResultStatus.Failed if errors else PluginResultStatus.Ok, errors)

    @classmethod
    def post_execute(cls, context: PluginContext, result: PluginResult):
        if not context.log:
            return

        log_func = context.log.info if result.status == PluginResultStatus.Ok else context.log.error
        log_func(f"Check '{cls.__name__}' finished with status: '{result.status}'")

        if result.status == PluginResultStatus.Ok:
            return

        if result.data:
            for file_path, (out, err) in result.data.items():
                context.log.error(f"Check formatting failed for file: '{file_path}'")
                if out:
                    context.log.error(f"With stdout:\n{out}")
                if err:
                    context.log.error(f"With stderr:\n{err}")
