"""Render shell completions from the CLI parser tree."""

from __future__ import annotations

import argparse
import shlex


def collect_completion_metadata(
    parser: argparse.ArgumentParser,
    path: tuple[str, ...] = (),
) -> dict[tuple[str, ...], dict[str, list[str]]]:
    """
    Collect subcommand and option metadata from an argparse tree.
    """
    metadata: dict[tuple[str, ...], dict[str, list[str]]] = {}
    options: list[str] = []
    subcommand_parsers: dict[str, argparse.ArgumentParser] = {}

    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, subparser in action.choices.items():
                subcommand_parsers[name] = subparser
            continue
        if action.option_strings and action.help != argparse.SUPPRESS:
            options.extend(action.option_strings)

    metadata[path] = {
        "options": sorted(dict.fromkeys(options)),
        "subcommands": sorted(subcommand_parsers),
    }

    for name, subparser in subcommand_parsers.items():
        metadata.update(collect_completion_metadata(subparser, path + (name,)))

    return metadata


def completion_key(path: tuple[str, ...]) -> str:
    """
    Render a shell-safe key for a parser path.
    """
    return "root" if not path else "__".join(path)


def powershell_quote(value: str) -> str:
    """
    Quote a literal string for PowerShell array output.
    """
    return "'" + value.replace("'", "''") + "'"


def render_bash_completion(program_name: str, metadata: dict[tuple[str, ...], dict[str, list[str]]]) -> str:
    """
    Render a bash completion function from parser metadata.
    """
    lines = [
        f"_{program_name}_completion() {{",
        "    local cur key",
        "    COMPREPLY=()",
        '    cur="${COMP_WORDS[COMP_CWORD]}"',
        "    key=root",
        "    for ((i=1; i<COMP_CWORD; i++)); do",
        '        case "$key:${COMP_WORDS[i]}" in',
    ]

    for path, node in metadata.items():
        key = completion_key(path)
        for subcommand in node["subcommands"]:
            next_key = completion_key(path + (subcommand,))
            lines.append(f"            {key}:{subcommand}) key={next_key} ;;")

    lines.extend(
        [
            "        esac",
            "    done",
            '    case "$key" in',
        ]
    )

    for path, node in metadata.items():
        key = completion_key(path)
        candidates = " ".join(node["subcommands"] + node["options"])
        lines.append(f'        {key}) COMPREPLY=( $(compgen -W {shlex.quote(candidates)} -- "$cur") ) ;;')

    lines.extend(
        [
            "    esac",
            "}",
            f"complete -F _{program_name}_completion {program_name}",
        ]
    )
    return "\n".join(lines) + "\n"


def render_zsh_completion(program_name: str, metadata: dict[tuple[str, ...], dict[str, list[str]]]) -> str:
    """
    Render a zsh completion function from parser metadata.
    """
    lines = [
        f"#compdef {program_name}",
        "",
        f"_{program_name}() {{",
        '  local key="root"',
        "  local -a candidates",
        "  local word",
        "  for (( i=2; i<CURRENT; i++ )); do",
        '    word="${words[i]}"',
        '    case "$key:$word" in',
    ]

    for path, node in metadata.items():
        key = completion_key(path)
        for subcommand in node["subcommands"]:
            next_key = completion_key(path + (subcommand,))
            lines.append(f'      {key}:{subcommand}) key="{next_key}" ;;')

    lines.extend(
        [
            "    esac",
            "  done",
            '  case "$key" in',
        ]
    )

    for path, node in metadata.items():
        key = completion_key(path)
        candidates = " ".join(shlex.quote(word) for word in (node["subcommands"] + node["options"]))
        lines.append(f"    {key}) candidates=({candidates}) ;;")

    lines.extend(
        [
            "  esac",
            "  _describe 'pyffmpegcore arguments' candidates",
            "}",
            "",
            f"compdef _{program_name} {program_name}",
        ]
    )
    return "\n".join(lines) + "\n"


def render_fish_completion(program_name: str, metadata: dict[tuple[str, ...], dict[str, list[str]]]) -> str:
    """Render Fish command and option completions from the argparse tree."""
    function_name = f"__{program_name}_completion_path"
    lines = [
        f"function {function_name}",
        "    set -l key root",
        "    set -l tokens (commandline -xpc)",
        "    for token in $tokens[2..-1]",
        '        switch "$key:$token"',
    ]
    for path, node in metadata.items():
        key = completion_key(path)
        for subcommand in node["subcommands"]:
            next_key = completion_key(path + (subcommand,))
            lines.extend([f"            case '{key}:{subcommand}'", f"                set key {next_key}"])
    lines.extend(["        end", "    end", "    echo $key", "end", f"complete -c {program_name} -f"])

    for path, node in metadata.items():
        condition = f"test ({function_name}) = {completion_key(path)}"
        for subcommand in node["subcommands"]:
            lines.append(f"complete -c {program_name} -n '{condition}' -a '{subcommand}'")
        for option in node["options"]:
            if option.startswith("--"):
                lines.append(f"complete -c {program_name} -n '{condition}' -l {option[2:]}")
            elif option.startswith("-") and len(option) == 2:
                lines.append(f"complete -c {program_name} -n '{condition}' -s {option[1:]}")
    return "\n".join(lines) + "\n"


def render_powershell_completion(
    program_name: str,
    metadata: dict[tuple[str, ...], dict[str, list[str]]],
) -> str:
    """
    Render a PowerShell argument completer from parser metadata.
    """
    lines = [
        f"Register-ArgumentCompleter -Native -CommandName {program_name} -ScriptBlock {{",
        "    param($wordToComplete, $commandAst, $cursorPosition)",
        "    $tokens = @($commandAst.CommandElements | Select-Object -Skip 1 | ForEach-Object { $_.Extent.Text })",
        "    if ($tokens.Count -eq 0) {",
        "        $previousTokens = @()",
        "    } elseif ($tokens.Count -eq 1) {",
        "        $previousTokens = @()",
        "    } else {",
        "        $previousTokens = $tokens[0..($tokens.Count - 2)]",
        "    }",
        '    $key = "root"',
        "    foreach ($token in $previousTokens) {",
        '        switch ("${key}:$token") {',
    ]

    for path, node in metadata.items():
        key = completion_key(path)
        for subcommand in node["subcommands"]:
            next_key = completion_key(path + (subcommand,))
            lines.append(f'            "{key}:{subcommand}" {{ $key = "{next_key}"; continue }}')

    lines.extend(
        [
            "        }",
            "    }",
            "    $candidates = switch ($key) {",
        ]
    )

    for path, node in metadata.items():
        key = completion_key(path)
        candidates = ", ".join(powershell_quote(word) for word in (node["subcommands"] + node["options"]))
        lines.append(f'        "{key}" {{ @({candidates}) }}')

    lines.extend(
        [
            "    }",
            '    $candidates | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {',
            "        [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)",
            "    }",
            "}",
        ]
    )
    return "\n".join(lines) + "\n"
