"""Reject oversized game saves before replacing any exported files."""
from logic import Cell  # Initialize the shared format-module search path.
from arrowasm import encode
from mapdata import write_map as _write_map
import re
from decimal import Decimal


def parse_save_size(value):
    """CLI size with explicit decimal/binary units; a bare integer is bytes."""
    match = re.fullmatch(r'\s*(\d+(?:\.\d+)?)\s*(B|KB|MB|GB|KiB|MiB|GiB)?\s*', value, re.I)
    if not match:
        raise ValueError('Укажите размер в байтах либо с единицей: 3MB, 3MiB, 1000KB.')
    units = dict(B=1, KB=1000, MB=1000**2, GB=1000**3,
                 KIB=1024, MIB=1024**2, GIB=1024**3)
    result = int(Decimal(match[1]) * units[(match[2] or 'B').upper()])
    if result <= 0:
        raise ValueError('Ограничение размера должно быть положительным.')
    return result


class SaveSizeError(ValueError):
    pass


def write_map(folder, stem, cells, max_save_bytes=None):
    payload = (encode(cells) + '\n').encode('ascii')
    size = len(payload)
    if max_save_bytes is not None and max_save_bytes <= 0:
        raise ValueError('Ограничение размера должно быть положительным.')
    if max_save_bytes is not None and size > max_save_bytes:
        raise SaveSizeError(
            f'Сохранение {stem}.save.txt: {size:,} байт; '
            f'заданный лимит {max_save_bytes:,} байт. '
            'Сборка отклонена, прежние файлы сохранены.'
        )
    _write_map(folder, stem, cells)
    # Fix the newline explicitly so the limit is identical on Windows/Linux.
    (folder / (stem + '.save.txt')).write_bytes(payload)
    return dict(save_bytes=size, save_limit_bytes=max_save_bytes)
