// A byte order mark survives copying between editors and would reach the compiler as a character
// of the code; both editors and the URL hash strip it
export function stripBom(value) {
    return value.replace(/\uFEFF/g, "");
}

// The single-byte Cyrillic table of CP1251: the character set db strings compile into,
// and the alphabet the code-in-URL scheme packs non-ASCII characters with
export const cp1251chars = "ЂЃ‚ѓ„…†‡€‰Љ‹ЊЌЋЏђ‘’“”•–—?™љ›њќћџ ЎўЈ¤Ґ¦§Ё©Є«¬­®Ї°±Ііґµ¶·ё№є»јЅѕїАБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдежзийклмнопрстуфхцчшщъыьэюя";
export const cp1251map = {};

for (let i = 0; i < cp1251chars.length; ++i)
    cp1251map[cp1251chars[i]] = 128 + i;
