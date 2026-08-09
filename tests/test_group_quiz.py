import pytest
from bot.routers.user_commands import user_command, group_command


def test_command_definitions():
    user_cmds = [c.command for c in user_command]
    group_cmds = [c.command for c in group_command]

    assert "start" in user_cmds
    assert "top" in user_cmds

    assert "quiz" in group_cmds
    assert "top" in group_cmds
    assert "help" in group_cmds
