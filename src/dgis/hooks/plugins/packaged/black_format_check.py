import tempfile
import sys

from pathlib import Path
from subprocess import PIPE, Popen
from typing import Optional

from dgis.hooks.plugins.plugin import Plugin, PluginContext, PluginResult, PluginResultPayload, PluginResultStatus
from dgis.hooks.utility.env import setup_env
from dgis.hooks.utility.git import parse_diff_ranges


class BlackFormatCheckPlugin(Plugin):
    _python_extension = ".py"

    @classmethod
    def _find_black_confing(cls, context: PluginContext) -> Optional[str]:
        black_config = None
        for obj in context.repo.tree("HEAD").traverse():
            if obj.type == "blob" and obj.name == "pyproject.toml":
                black_config = obj.hexsha
                break
        return black_config

    @classmethod
    def execute(cls, context: PluginContext) -> PluginResult:
        payloads = None

        # Always invoke black via the current Python interpreter to avoid PATH issues
        script_cmd = [sys.executable, "-m", "black"]

        # Prepare environment for subprocess so the child process can import local packages if needed
        env = setup_env()

        with tempfile.TemporaryDirectory() as tmp_dir:
            if context.log:
                context.log.debug(f"Running in temp dir: '{tmp_dir}'")

            black_config = cls._find_black_confing(context)
            black_config_tmp_path = Path(tmp_dir) / "pyproject.toml"
            if black_config:
                if context.log:
                    context.log.debug(f"Found black config (pyproject.toml) HEXSHA: '{black_config}'")
                with open(black_config_tmp_path, "wb") as file:
                    file.write(context.repo.git.cat_file("blob", black_config).encode())
            else:
                if context.log:
                    context.log.warning(f"No black config (pyproject.toml) file found while executing '{cls.__name__}'")
                return PluginResult(PluginResultStatus.Ok, None)

            diff = context.ref.diff(context.repo)
            for diff_content in diff:
                if diff_content.deleted_file:
                    continue

                if diff_content.renamed_file and not diff_content.b_blob:
                    continue

                if not diff_content.b_path.endswith(cls._python_extension):
                    if context.log:
                        context.log.debug(f"Skipping non-py file: '{diff_content.b_path}'")
                    continue

                if not diff_content.diff:
                    if context.log:
                        context.log.debug(f"Skipping no-diff file: '{diff_content.b_path}'")
                    continue

                diff_str = diff_content.diff
                if isinstance(diff_str, (bytearray, bytes)):
                    try:
                        diff_str = diff_content.diff.decode()
                    except Exception:  # pylint: disable=broad-except
                        if context.log:
                            context.log.debug(f"Failed to decode diff: '{diff_content.diff}'")
                        continue

                diff_ranges = [f"--line-ranges={start}-{end}" for start, end in parse_diff_ranges(diff_str)]

                file_path = Path(tmp_dir) / diff_content.b_path
                if len(file_path.parents) > 0 and not file_path.parent.exists():
                    file_path.parent.mkdir(parents=True)

                with open(file_path, "wb") as file:
                    file.write(context.repo.git.cat_file("blob", diff_content.b_blob.hexsha).encode())

                if context.log:
                    context.log.debug(f"Executing '{cls.__name__}' for file: '{file_path}'")

                # Call black in --diff mode to detect formatting changes
                black_call = script_cmd + [
                    "--config",
                    str(black_config_tmp_path),
                    "--color",
                    "--diff",
                    *diff_ranges,
                    str(file_path),
                ]
                if context.log:
                    context.log.debug(f"Calling black tool: {' '.join(map(str, black_call))}")

                p = Popen(black_call, stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=str(Path(tmp_dir)), env=env)
                out, err = p.communicate()

                # Black prints a diff to stdout when it would reformat a file.
                # Treat presence of stdout (non-empty) as a formatting error.
                if out and out.strip():
                    try:
                        out_dec = out.decode()
                    except Exception:  # pylint: disable=broad-except
                        out_dec = None
                    try:
                        err_dec = err.decode() if err else None
                    except Exception:  # pylint: disable=broad-except
                        err_dec = None

                    file_path = file_path.relative_to(Path(tmp_dir))
                    if not payloads:
                        payloads = [PluginResultPayload(stdout=out_dec, stderr=err_dec, diff=out_dec, file=file_path)]
                    else:
                        payloads.append(
                            PluginResultPayload(stdout=out_dec, stderr=err_dec, diff=out_dec, file=file_path)
                        )

        if not payloads:
            return PluginResult(PluginResultStatus.Ok, None)

        return PluginResult(PluginResultStatus.Failed, payloads)

    @classmethod
    def post_execute(cls, context: PluginContext, result: PluginResult):
        if not context.log:
            return

        log_func = context.log.info if result.status == PluginResultStatus.Ok else context.log.error
        log_func(f"Check '{cls.__name__}' finished with status: '{result.status.colored()}'")

        if result.status == PluginResultStatus.Ok:
            return

        if result.payloads:
            for payload in result.payloads:
                context.log.error(f"Check formatting failed for file: '{payload.file}'")
                if payload.stdout:
                    context.log.error(f"With stdout:\n{payload.stdout}")
                if payload.stderr:
                    context.log.error(f"With stderr:\n{payload.stderr}")
