import os
import sys
import re
import shutil
import zipfile
import datetime
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox, filedialog

DLL_LIST = [
    'libcrypto-3-x64.dll',
    'libssl-3-x64.dll',
    'uibase.dll',
    'usvfs_x64.dll',
    'usvfs_x86.dll'
]

BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
MODS_DIR = os.path.join(BASE_DIR, "mods")
BACKUP_DIR = os.path.join(BASE_DIR, "_MO2 meta.ini Backup")
EXAMPLE_FILE = os.path.join(BACKUP_DIR, "example.txt")

def check_dlls():
    for dll in DLL_LIST:
        if not os.path.exists(os.path.join(BASE_DIR, dll)):
            messagebox.showerror("오류", "ModOrganizer2.exe가 위치한 폴더에 넣어주세요")
            sys.exit(1)

placeholder_text = (
    "MO2 창에서 바꾸고 싶은 모드들을 선택한 뒤,\nCtrl+C키 등을 이용하여 복사하고 여기에 붙여넣으세요\n"
    "선택한 모드들의 이름이 그대로 나와야 합니다.\n\n"
    "ex)\nIsland Cloud Removal\nTime Eternal v2.0\nKeep Inventory On Death v2.0"
)



# =======================================================================
def get_selected_mod_names(text_widget):
    raw = text_widget.get("1.0", "end-1c")

    if raw.strip() == placeholder_text.strip():
        return []
    return [line.strip() for line in raw.splitlines() if line.strip()]

def get_filtered_meta_files(selected_names):
    meta_files = []
    for root, _, files in os.walk(MODS_DIR):
        if os.path.basename(root).lower().endswith("_separator"):
            continue
        if os.path.basename(root) in selected_names:
            for file in files:
                if file.lower() == "meta.ini":
                    meta_files.append(os.path.join(root, file))
    return meta_files


# (1a)--------------------------------------------------------------------
def backup_meta_files(selected_names, text_widget, show_message=True):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    now = datetime.datetime.now().strftime("bak_%y%m%d_%H%M%S")
    zip_name = os.path.join(BACKUP_DIR, f"{now}.zip")
    index = 1

    meta_files = get_filtered_meta_files(selected_names)
    existing_mods = [os.path.basename(os.path.dirname(p)) for p in meta_files]
    not_found = [name for name in selected_names if name not in existing_mods]

    if not selected_names:
        if show_message:
            messagebox.showinfo("백업 오류", "아직 입력된 내용이 없어 백업파일을 생성할 수 없습니다.")
        return
    else:
        if not meta_files:
            if show_message:
                messagebox.showerror("백업 실패", 
                    "입력된 모든 모드명이 존재하지 않거나 meta.ini 파일을 포함하고 있지 않습니다. "
                    "다시 확인해주세요.")
            return
        else:
            if not_found and show_message == True:
                messagebox.showwarning("백업 오류", f"다음 모드명은 존재하지 않아 백업에서 제외됩니다:\n\n" + "\n".join(not_found))

            while os.path.exists(zip_name):
                zip_name = os.path.join(BACKUP_DIR, f"{now} ({index}).zip")
                index += 1
            with zipfile.ZipFile(zip_name, 'w') as zipf:
                for meta in meta_files:
                    arcname = os.path.relpath(meta, MODS_DIR)
                    zipf.write(meta, arcname)
            if show_message == True:
                messagebox.showinfo("백업 완료", f"\"{os.path.basename(zip_name)}\"\n로 백업되었습니다.")


# (1b)--------------------------------------------------------------------
def restore_latest_backup_by_file(text_editor):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    zip_path = filedialog.askopenfilename(initialdir=BACKUP_DIR, filetypes=[("ZIP files", "*.zip")])
    if not zip_path:
        return

    with zipfile.ZipFile(zip_path, 'r') as zipf:
        mod_names = set([
            name.split('/')[0] for name in zipf.namelist()
            if name.endswith("meta.ini") and "/" in name])
        mod_names = list(mod_names)
    backup_meta_files(mod_names, text_editor, show_message=False)

    with zipfile.ZipFile(zip_path, 'r') as zipf:
        zipf.extractall(MODS_DIR)
    messagebox.showinfo("복원 완료", f"\"{os.path.basename(zip_path)}\"를 복원했습니다.")


# (4)--------------------------------------------------------------------
def on_click_output(ent_add_front, ent_add_back, ent_rem_front, ent_rem_back,
    ent_add_front_pos, ent_add_back_pos, ent_rem_front_pos, ent_rem_back_pos,
    text_editor):

    add_front = ent_add_front.get()
    add_back = ent_add_back.get()
    rem_front = ent_rem_front.get()
    rem_back = ent_rem_back.get()
    if not (add_front or add_back or rem_front or rem_back):
        messagebox.showwarning("출력 오류", "추가/제거할 문자가 입력되지 않았습니다.")
        return
    else:
        backup_meta_files(get_selected_mod_names(text_editor), text_editor, show_message=False)
        modify_comments(
            add_front, add_back,
            rem_front, rem_back,
            int(ent_add_front_pos.get() or 0), int(ent_add_back_pos.get() or 0),
            int(ent_rem_front_pos.get() or 0), int(ent_rem_back_pos.get() or 0),
            apply_changes=True, text_widget=text_editor)


# (2,3,4)--------------------------------------------------------------------
def modify_comments(prefix_add, suffix_add, prefix_remove, suffix_remove, prefix_add_pos, 
    suffix_add_pos, prefix_rem_pos, suffix_rem_pos, text_widget=None, apply_changes=False):
    count = 0
    selected_names = get_selected_mod_names(text_widget) if text_widget else []
    meta_files = get_filtered_meta_files(selected_names)
    existing_mods = [os.path.basename(os.path.dirname(p)) for p in meta_files]
    not_found = [name for name in selected_names if name not in existing_mods]
    example_lines = [
        "---------------",
        "[모드명]",
        "(메모 - 변경전)",
        "(메모 - 변경후)",
        "---------------",
        ""]


    if get_selected_mod_names(text_widget):
        if not meta_files:
            messagebox.showerror("오류", 
                "입력된 모든 모드명이 존재하지 않거나 meta.ini 파일을 포함하고 있지 않습니다. "
                "다시 확인해주세요.")
        else:
            if not_found:
                messagebox.showwarning("오류", f"다음 모드명은 존재하지 않아 제외됩니다:\n\n" + "\n".join(not_found))


            for path in meta_files:
                with open(path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                changed = False
                rel_path = os.path.relpath(path, MODS_DIR).replace("\\meta.ini", "").replace("/meta.ini", "")
                for i, line in enumerate(lines):
                    match = re.search(r'comments="([^"]*)"', line)
                    if match:
                        content = match.group(1)
                        orig = content

                        if prefix_add:
                            content = content[:prefix_add_pos] + prefix_add + content[prefix_add_pos:]
                        if prefix_remove and content[prefix_rem_pos:prefix_rem_pos+len(prefix_remove)] == prefix_remove:
                            content = content[:prefix_rem_pos] + content[prefix_rem_pos+len(prefix_remove):]

                        if suffix_add:
                            idx = len(content) - suffix_add_pos
                            content = content[:idx] + suffix_add + content[idx:]
                        idx = len(content) - suffix_rem_pos
                        if suffix_remove and content[idx-len(suffix_remove):idx] == suffix_remove:
                            content = content[:idx-len(suffix_remove)] + content[idx:]

                        if content != orig:
                            changed = True
                            lines[i] = re.sub(r'comments="[^"]*"', f'comments="{content}"', line)

                        example_lines.append(f"{rel_path}")
                        example_lines.append(f"{orig}")
                        example_lines.append(f"{content}")
                        example_lines.append("")

                if changed and apply_changes:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    count += 1

            if not apply_changes:
                os.makedirs(BACKUP_DIR, exist_ok=True)
                with open(EXAMPLE_FILE, 'w', encoding='utf-8') as f:
                    f.write("\n".join(example_lines))
                os.startfile(EXAMPLE_FILE)
            else:
                if count == 0:
                    messagebox.showinfo("완료", "변경된 meta.ini 파일이 없습니다.")
                else:
                    messagebox.showinfo("완료", f"총 {count}개의 meta.ini 파일을 변경했습니다.")
    else:
        messagebox.showinfo("출력 오류", "아직 입력된 내용이 없습니다.")






# =======================================================================
def build_gui():
    check_dlls()

    root = tk.Tk()
    root.title("MO2 Notes pre/suffix Editor")
    root.geometry("900x640")
    root.minsize(550, 640)
    root.configure(bg="#F0F0F0")

    default_font = tkfont.nametofont("TkDefaultFont")
    default_font.configure(size=10)
    root.option_add("*Button.Relief", "groove")
    root.option_add("*Button.Background", "#E1E1E1")

    def on_closing():
        add_front = ent_add_front.get().strip()
        add_back = ent_add_back.get().strip()
        rem_front = ent_rem_front.get().strip()
        rem_back = ent_rem_back.get().strip()
        text_content = text_editor.get("1.0", "end").strip()
        has_real_text = text_content and text_content != placeholder_text.strip()
        if add_front or add_back or rem_front or rem_back or has_real_text:
            if not messagebox.askyesno("종료 확인", "입력된 값이 있습니다. 정말 종료하시겠습니까?"):
                return
        root.destroy()

    main_frame = tk.Frame(root, bg="#F0F0F0")
    main_frame.pack(fill="both", expand=True)
    left_frame = tk.Frame(main_frame, width=500, bg="#F0F0F0")
    left_frame.pack(side="left", fill="both", expand=False)



# (1)--------------------------------------------------------------------
    tk.Label(
        left_frame, 
        text="\n\n모드의 모든 메모 앞뒤에 문자를 추가/제거하는 프로그램입니다\n\"meta.ini\"파일을 미리 백업한 뒤 사용해주세요\n\n"
    ).pack()

    # 백업 프레임
    frame_bak = tk.LabelFrame(left_frame, text="[ Meta.ini 백업 ]", font=("default_font", 10, "bold"))
    frame_bak.pack(fill="x", padx=5, pady=5)
    bak_frame = tk.Frame(frame_bak)
    bak_frame.pack()

    tk.Button(bak_frame,text="백업 생성하기",
        command=lambda: backup_meta_files(get_selected_mod_names(text_editor), text_editor), width=20, height=2
        ).pack(side="left", padx=10)    
    tk.Button(bak_frame, text="백업 불러오기", command=lambda: restore_latest_backup_by_file(text_editor), 
        width=20, height=2).pack(side="left", padx=10, pady=5)
    tk.Label(
        left_frame, 
        text="( \"백업 불러오기\" 클릭시, 백업이 자동으로 생성됩니다 )\n( 백업위치 : MO2 폴더 - \"_MO2 meta.ini Backup\"폴더 )\n"
    ).pack()


# (2)--------------------------------------------------------------------
    frame_add = tk.LabelFrame(left_frame, text="[ 문자 추가하기 ]", font=("default_font", 10, "bold"))
    frame_add.pack(fill="x", padx=5, pady=5)

    tk.Label(frame_add, text=" ", width=0).pack(side="left")
    tk.Label(frame_add, text="앞:", width=2).pack(side="left")
    ent_add_front = tk.Entry(frame_add, width=18)
    ent_add_front_pos = tk.Entry(frame_add, width=4)
    ent_add_front_pos.insert(0, "0")
    ent_add_front.pack(side="left", padx=4)
    ent_add_front_pos.pack(side="left")

    tk.Label(frame_add, text=" ", width=0).pack(side="left")
    tk.Label(frame_add, text="뒤:", width=2).pack(side="left")
    ent_add_back = tk.Entry(frame_add, width=18)
    ent_add_back_pos = tk.Entry(frame_add, width=4)
    ent_add_back_pos.insert(0, "0")
    ent_add_back.pack(side="left", padx=4)
    ent_add_back_pos.pack(side="left", pady=5)


# (3)--------------------------------------------------------------------
    frame_rem = tk.LabelFrame(left_frame, text="[ 문자 제거하기 ]", font=("default_font", 10, "bold"))
    frame_rem.pack(fill="x", padx=5, pady=5)

    tk.Label(frame_rem, text=" ", width=0).pack(side="left")
    tk.Label(frame_rem, text="앞:", width=2).pack(side="left")

    ent_rem_front = tk.Entry(frame_rem, width=18)
    ent_rem_front_pos = tk.Entry(frame_rem, width=4)
    ent_rem_front_pos.insert(0, "0")
    ent_rem_front.pack(side="left", padx=4)
    ent_rem_front_pos.pack(side="left")

    tk.Label(frame_rem, text=" ", width=0).pack(side="left")
    tk.Label(frame_rem, text="뒤:", width=2).pack(side="left")
    ent_rem_back = tk.Entry(frame_rem, width=18)
    ent_rem_back_pos = tk.Entry(frame_rem, width=4)
    ent_rem_back_pos.insert(0, "0")
    ent_rem_back.pack(side="left", padx=4)
    ent_rem_back_pos.pack(side="left", pady=5)
    tk.Label(frame_rem, text=" ", width=1).pack(side="left")

    tk.Label(
        left_frame, 
        text="( 작은 칸에는 문자가 추가/제거될 위치를 적어주세요 )\n"
        "( 앞/뒤에서 x번째의 문자를 추가/제거한다는 의미입니다. 기본값=0 )\n"
    ).pack()


# (4)--------------------------------------------------------------------
    frame_btn = tk.LabelFrame(left_frame, text="[ 출력 ]", font=("default_font", 10, "bold"))
    frame_btn.pack(fill="x", padx=5, pady=5)
    btn_frame = tk.Frame(frame_btn)
    btn_frame.pack()

    tk.Button(btn_frame, text="예시 확인하기", command=lambda: modify_comments(
        ent_add_front.get(), ent_add_back.get(),
        ent_rem_front.get(), ent_rem_back.get(),
        int(ent_add_front_pos.get() or 0), int(ent_add_back_pos.get() or 0),
        int(ent_rem_front_pos.get() or 0), int(ent_rem_back_pos.get() or 0),
        apply_changes=False, text_widget=text_editor),
        width=20, height=2).pack(side="left", padx=10)

    tk.Button(btn_frame, text="최종 출력하기", command=lambda: on_click_output(
        ent_add_front, ent_add_back, ent_rem_front, ent_rem_back,
        ent_add_front_pos, ent_add_back_pos, ent_rem_front_pos, ent_rem_back_pos,
        text_editor), 
        width=20, height=2).pack(side="left", padx=10, pady=5)
    tk.Label(left_frame, text="( \"최종 출력하기\" 클릭시, 백업이 자동으로 생성됩니다 )\n\n").pack(pady=1)


# (5)--------------------------------------------------------------------
    frame_end = tk.LabelFrame(left_frame)
    frame_end.pack(padx=10, pady=5)
    tk.Label(
        frame_end,
        text="MO2 Notes pre/suffix Editor - v1.0",
        font=("default_font", 10, "bold")
    ).pack(padx=5, pady=(5,2))
    tk.Label(
        frame_end,
        text="( github.com/GingerSodium )",
        font=("default_font", 10)
    ).pack(padx=5, pady=(0,5))


# (6)--------------------------------------------------------------------
    right_frame = tk.Frame(main_frame, width=500)
    right_frame.pack(side="left", fill="both", expand=True)
    editor_container = tk.Frame(right_frame)
    editor_container.pack(fill="both", expand=True, padx=5, pady=5)

    text_editor = tk.Text(editor_container, wrap="word", font=("Consolas", 10), undo=True)
    text_editor.grid(row=0, column=0, sticky="nsew")
    text_editor.bind("<Control-z>", lambda event: text_editor.edit_undo())
    text_editor.bind("<Control-y>", lambda event: text_editor.edit_redo())

    def show_placeholder():
        text_editor.config(fg="gray")
        text_editor.delete("1.0", "end")
        text_editor.insert("1.0", placeholder_text)

    def hide_placeholder():
        if text_editor.get("1.0", "end-1c").strip() == placeholder_text:
            text_editor.delete("1.0", "end")
            text_editor.config(fg="black")

    def on_key_release(event):
        content = text_editor.get("1.0", "end-1c").strip()
        if content == "":
            show_placeholder()
        elif content == placeholder_text:
            pass
        else:
            text_editor.config(fg="black")

    def on_key_press(event):
        if text_editor.get("1.0", "end-1c").strip() == placeholder_text:
            hide_placeholder()

    text_editor = tk.Text(editor_container, wrap="none", font=("Consolas", 10), undo=True)
    text_editor.grid(row=0, column=0, sticky="nsew")
    text_editor.bind("<KeyPress>", on_key_press)
    text_editor.bind("<KeyRelease>", on_key_release)
    show_placeholder()

    scrollbar_y = tk.Scrollbar(editor_container, command=text_editor.yview)
    scrollbar_y.grid(row=0, column=1, sticky="ns")
    text_editor.config(yscrollcommand=scrollbar_y.set)

    scrollbar_x = tk.Scrollbar(editor_container, orient="horizontal", command=text_editor.xview)
    scrollbar_x.grid(row=1, column=0, sticky="ew")
    text_editor.config(xscrollcommand=scrollbar_x.set)

    editor_container.grid_rowconfigure(0, weight=1)
    editor_container.grid_columnconfigure(0, weight=1)


# =======================================================================
    root.mainloop()
if __name__ == "__main__":
    build_gui()