import shutil
from pathlib import Path
from subprocess import PIPE, Popen
from typing import Optional

from git import Repo

from dgis.hooks.plugins.plugin import Plugin, PluginContext, PluginResult, PluginResultStatus
from dgis.hooks.utility.common import temp_dir


class ClangFormatCheckPlugin(Plugin):
    @classmethod
    def _find_clang_format_style_path(cls, repo: Repo) -> Optional[Path]:
        clang_format_style_path = None
        for obj in repo.tree("HEAD").traverse():
            if obj.type == "blob" and obj.name == ".clang-format":
                clang_format_style_path = obj.abspath
                break
        return Path(clang_format_style_path)

    @classmethod
    def execute(cls, context: PluginContext) -> PluginResult:
        errors = {}

        binary_path = "clang-format"
        tmp_dir = Path("temp-for-format")

        with temp_dir(tmp_dir):
            clang_format_style_path = cls._find_clang_format_style_path(context.repo)
            if clang_format_style_path:
                shutil.copy2(clang_format_style_path, tmp_dir / clang_format_style_path.name)
            else:
                if context.log:
                    context.log.warning(f"No clang-format style file found while executing '{cls.__name__}'")
                return PluginResult(PluginResultStatus.Ok, None)

            diff = context.ref.diff(context.repo)
            for diff_content in diff:
                if diff_content.deleted_file:
                    continue

                repo_file_path = Path(context.repo.working_dir) / diff_content.b_path
                file_path = tmp_dir / repo_file_path.name
                if file_path.suffix not in [".cpp", ".c", ".h", ".hpp", ".hqt"]:
                    continue
                else:
                    shutil.copy2(repo_file_path, file_path)

                if context.log:
                    context.log.debug(f"Executing '{cls.__name__}' for file: '{file_path}'")

                diff_file_path = (tmp_dir / file_path.name).with_suffix(".diff")
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
                    f"-style=file",
                    f"-filesrc={file_path.absolute()}",
                    f"-filediff={diff_file_path.absolute()}",
                    f"-binary={binary_path}",
                    f"-workdir={tmp_dir.absolute()}",
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
                context.log.error(f"Check JSON failed for file: '{file_path}' with out:\n '{out}' and err:\n '{err}'")
