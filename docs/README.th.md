# Multilevel Number Indent สำหรับ Notepad++

[English](../README.md) · **ภาษาไทย**

เคยใช้เลขหัวข้อหลายชั้นใน Word ไหมคะ แบบที่กด Tab แล้ว `2.` กลายเป็น `1.1.` เลขข้างล่างก็เรียงใหม่ให้เอง ตัวนี้คือแบบนั้นแหละ แต่อยู่ใน Notepad++ และเป็นข้อความธรรมดาล้วน ๆ

```
1. top
	1.1. Media
		1.1.1. use
			1) a
			2) b
		1.1.2. problem
			1) d        ← ข้อย่อยชุดใหม่เริ่มที่ 1) เสมอ
			2) e
```

ไม่มี format ซ่อน ไม่ต้องใช้ไฟล์ชนิดพิเศษ ก๊อปไปวางในอีเมล แชต หรือ Git ก็ยังหน้าตาเหมือนเดิม

ตัวนี้แตกมาจาก[ปลั๊กอิน Obsidian](https://github.com/AlungranPJ/obsidian-multilevel-number-indent) ค่ะ แทนที่จะเขียนกฎนับเลขใหม่อีกรอบแล้วเพี้ยนกันนิด ๆ หน่อย ๆ ก็เลยเรียก engine ตัวเดียวกันเลย รายการเดียวกันจะได้เลขเหมือนกันทั้งสองโปรแกรม

## ติดตั้ง

ต้องมี Windows, [Notepad++](https://notepad-plus-plus.org) และ [Node.js](https://nodejs.org) (ถ้ายังไม่มี ตัวติดตั้งจะถามว่าจะลงให้ไหม)

**วิธีง่ายสุด** โหลด [`npp-multilevel-number-indent.zip`](https://github.com/AlungranPJ/notepadpp-multilevel-number-indent/releases/latest/download/npp-multilevel-number-indent.zip) แตกไฟล์ แล้วดับเบิลคลิก **`install.cmd`**

**หรือพิมพ์บรรทัดเดียวใน PowerShell:**

```powershell
irm https://github.com/AlungranPJ/notepadpp-multilevel-number-indent/releases/latest/download/install.ps1 | iex
```

ตัวติดตั้งจะ

1. หา Notepad++ แล้วขอปิดก่อน (Notepad++ เขียนทับ setting ตอนปิด แก้ตอนเปิดอยู่ก็หายหมด)
2. เช็กว่ามี Node.js
3. ลงปลั๊กอิน **PythonScript 3** ให้ถ้ายังไม่มี ขั้นนี้ Windows จะถามสิทธิ์ admin หนึ่งครั้ง เพราะ Notepad++ โหลดปลั๊กอินจาก `Program Files` เท่านั้น
4. ก๊อป engine ไปไว้ที่ `%APPDATA%\Notepad++\plugins\config`
5. เพิ่มเมนูให้

ไฟล์ของ Notepad++ ที่แก้ จะสำรองเป็น `*.mni-backup` ไว้ก่อนทุกไฟล์ เสร็จแล้วเปิด Notepad++ พิมพ์ `1. ` ในไฟล์ `.txt` แล้วกด Enter ได้เลย

> **ทำไมไม่ลงจาก Plugins Admin?** ใน Plugins Admin มีแต่ PythonScript 2.1 ซึ่งเป็น Python 2 ใช้กับตัวนี้ไม่ได้ ตัวติดตั้งเลยไปโหลด 3.0.27 จาก [GitHub ของเขา](https://github.com/bruderstein/PythonScript/releases) มาให้

อยากเอาออกก็ดับเบิลคลิก `uninstall.cmd` ส่วน PythonScript จะเก็บไว้ เผื่อมีสคริปต์อื่นใช้อยู่

## ปุ่มลัด

| ปุ่ม | บนบรรทัดที่มีเลข |
|---|---|
| <kbd>Enter</kbd> | ขึ้นเลขถัดไประดับเดียวกัน cursor อยู่หลังเลขพอดี |
| <kbd>Tab</kbd> | ลงไปหนึ่งระดับ (`2.` → `1.1.`) เลขข้างล่างเรียงใหม่ให้ |
| <kbd>Shift</kbd>+<kbd>Tab</kbd> | ขึ้นมาหนึ่งระดับ |
| <kbd>Alt</kbd>+<kbd>↑</kbd> / <kbd>↓</kbd> | สลับกับข้อข้างบนหรือข้างล่าง ข้อย่อยตามไปด้วย |
| <kbd>Ctrl</kbd>+<kbd>Z</kbd> | ย้อนทั้งการย้ายในครั้งเดียว |

เลือกหลายข้อก่อนแล้วกด Tab, Shift+Tab หรือ Alt+↑/↓ จะย้ายไปทั้งก้อน แถมยังเลือกค้างไว้ให้กดต่อได้อีก

ทำงานเฉพาะบรรทัดที่มีเลข ในไฟล์ `.txt`, `.md` และไฟล์ใหม่ที่ยังไม่ตั้งชื่อ ถ้าเป็นไฟล์โค้ด บรรทัดไม่มีเลข เลือกแบบ column มีหลาย cursor หรือ autocomplete เด้งอยู่ ทุกปุ่มทำงานแบบ Notepad++ ปกติ

## เมนูคลิกขวา

คลิกขวา → **Multilevel list section**

| คำสั่ง | ทำอะไร |
|---|---|
| Reset numbering | เรียงเลขใหม่ตั้งแต่ต้น แก้เลขข้ามหรือซ้ำ |
| Add numbering | ใส่เลขให้บรรทัดที่เลือก |
| Remove numbering | เอาเลขออก เก็บข้อความไว้ |
| Clear formatting | เอาทั้งเลขและย่อหน้าออก |
| Tidy up list | จัดย่อหน้าและเลขให้เรียบร้อย |
| Convert to numbered list | แปลง bullet, เลขแบบ `1.2.3` หรือ `a)` ที่วางมา ให้เป็นรูปแบบนี้ |
| Change list level | ย้ายข้อไประดับที่พิมพ์ใส่ |
| Number headings | ใส่เลข `1.`, `1.1.` ให้หัวข้อ `#` ของ Markdown |
| Remove heading numbers | เอาเลขหัวข้อออก |
| Copy as plain text | ก๊อปส่วนที่เลือกโดยไม่เอาเลข |

คำสั่งชุดเดียวกัน บวก **Numbering keys on or off** อยู่ที่ Plugins → Python Script → Scripts ด้วย อยากผูกปุ่มลัดเองก็ตั้งได้ที่ Settings → Shortcut Mapper

## ตั้งค่า

`%APPDATA%\Notepad++\plugins\config\MultilevelNumberIndent\settings.json`

```json
{
  "enabled": true,
  "node": "C:\\Program Files\\nodejs\\node.exe",
  "formats": ["1.", "1.1.", "1.1.1.", "1)", "1.1)", "1.1.1)"]
}
```

`formats` คือรูปแบบเลขของแต่ละระดับ เหมือนใน Obsidian: `1.` เลข, `a)` ตัวอักษร, `i.` เลขโรมัน, `1.1.` ต่อเลขจากข้อแม่ แก้แล้วปิดเปิด Notepad++ ใหม่นะคะ

## ถ้ามีอะไรแปลก ๆ

- **กดแล้วไม่มีอะไรเกิดขึ้น** เปิด `mni.log` ข้าง ๆ `settings.json` ดู ต้องมีคำว่า `engine ready` ถ้าบอกว่าหา Node ไม่เจอ ให้แก้ `node` ใน `settings.json`
- **ไม่มี "Multilevel list section" ในเมนู** แปลว่าตอนติดตั้ง Notepad++ เปิดอยู่ ปิดแล้วรัน `install.cmd` อีกรอบ
- **อยากปิดชั่วคราว** Plugins → Python Script → Scripts → Numbering keys on or off

## สัญญาอนุญาต

MIT ส่วน PythonScript เป็น GPL-2.0 ตัวติดตั้งโหลดจากที่ของเขาเอง ไม่ได้รวมไว้ใน repo นี้
