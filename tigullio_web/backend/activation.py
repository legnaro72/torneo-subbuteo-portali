"""Shared access policy; inspecting credentials never changes or exposes them."""


def credential_present(player):
    value = player.get('Password')
    return isinstance(value, str) and bool(value.strip())


def password_flag(player):
    value = player.get('SetPwd')
    return value == 1 or value == '1'


def activation_state(player):
    role = player.get('Ruolo', 'R')
    if role == 'R':
        return 'reader'
    if role not in ('A', 'W'):
        return 'review'
    present, flag = credential_present(player), password_flag(player)
    if present and flag:
        return 'active'
    if not present and not flag:
        return 'pending'
    return 'review'
