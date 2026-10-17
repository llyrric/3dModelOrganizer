#!/usr/bin/env python3
"""
3D Printing Library Organizer - File Reassignment CLI Tool
Easily reassign and move 3D files/archives to a different category and folder.
"""

import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import argparse
import reassign_core


def format_bold(text):
    return f"\033[1m{text}\033[0m"

def format_cyan(text):
    return f"\033[96m{text}\033[0m"

def format_green(text):
    return f"\033[92m{text}\033[0m"

def format_yellow(text):
    return f"\033[93m{text}\033[0m"

def format_red(text):
    return f"\033[91m{text}\033[0m"

def interactive_mode():
    print("=" * 70)
    print(format_bold(format_cyan("  📦 3D Model File Reassignment & Move Wizard")))
    print("=" * 70)
    print()

    # Load structure & library data
    print("Loading library catalog...")
    lib_data = reassign_core.load_library_data()
    structure = reassign_core.get_library_structure()
    categories = structure["categories"]
    folders_by_cat = structure["foldersByCategory"]

    # 1. Search for file
    query = input(format_bold("🔍 Enter file name or keyword to search: ")).strip()
    if not query:
        print(format_red("No search term entered. Exiting."))
        return

    # Find matches in libraryData
    matches = []
    q_lower = query.lower()
    for col in lib_data:
        cat = col.get("Category", "")
        creator = col.get("Creator", "")
        for it in col.get("Items", []):
            it_name = it.get("name", "")
            if q_lower in it_name.lower():
                matches.append({
                    "category": cat,
                    "creator": creator,
                    "name": it_name,
                    "thumb": it.get("thumb")
                })
        if len(matches) >= 30:
            break

    if not matches:
        print(format_yellow(f"No files matching '{query}' found in library catalog."))
        return

    print(f"\nFound {len(matches)} matching file(s):")
    for i, m in enumerate(matches, 1):
        print(f"  [{format_cyan(str(i))}] {format_bold(m['name'])}")
        print(f"      📍 Current Location: {m['category']} ➔ {m['creator']}")

    choice_str = input(f"\nSelect file number (1-{len(matches)}) or [C]ancel: ").strip()
    if not choice_str.isdigit() or not (1 <= int(choice_str) <= len(matches)):
        print("Cancelled.")
        return

    selected = matches[int(choice_str) - 1]
    src_cat = selected["category"]
    src_creator = selected["creator"]
    file_name = selected["name"]

    print(f"\nSelected: {format_green(file_name)}")
    print(f"From: {format_cyan(src_cat)} / {format_cyan(src_creator)}")

    # 2. Select destination category
    print("\n" + format_bold("📁 Destination Category:"))
    for i, cat in enumerate(categories, 1):
        current_indicator = " (current)" if cat == src_cat else ""
        print(f"  [{i:2d}] {cat}{current_indicator}")
    print("  [ N] + Create New Category")

    cat_choice = input("\nSelect category number or type category name: ").strip()
    if cat_choice.lower() == 'n':
        dest_cat = input("Enter new category name: ").strip()
    elif cat_choice.isdigit() and 1 <= int(cat_choice) <= len(categories):
        dest_cat = categories[int(cat_choice) - 1]
    elif cat_choice in categories:
        dest_cat = cat_choice
    else:
        dest_cat = cat_choice

    if not dest_cat:
        print(format_red("Category cannot be empty."))
        return

    # 3. Select destination folder/creator
    existing_folders = folders_by_cat.get(dest_cat, [])
    print(f"\n" + format_bold(f"📂 Destination Folder in '{dest_cat}':"))
    if existing_folders:
        limit = min(25, len(existing_folders))
        for i, folder in enumerate(existing_folders[:limit], 1):
            curr = " (current)" if (dest_cat == src_cat and folder == src_creator) else ""
            print(f"  [{i:2d}] {folder}{curr}")
        if len(existing_folders) > limit:
            print(f"  ... and {len(existing_folders) - limit} more")
    print("  [ N] + Create New Folder / Type Custom Name")

    folder_choice = input("\nSelect folder number, or type folder name: ").strip()
    if folder_choice.lower() == 'n':
        dest_creator = input("Enter new folder name: ").strip()
    elif folder_choice.isdigit() and 1 <= int(folder_choice) <= len(existing_folders):
        dest_creator = existing_folders[int(folder_choice) - 1]
    else:
        dest_creator = folder_choice

    if not dest_creator:
        print(format_red("Folder name cannot be empty."))
        return

    # 4. Optional rename
    disk_file, _ = reassign_core.clean_file_display_name(file_name)
    rename_prompt = input(f"\nRename file? (Press ENTER to keep '{disk_file}'): ").strip()
    new_name = rename_prompt if rename_prompt else None

    # Summary and confirmation
    print("\n" + "=" * 70)
    print(format_bold("MOVE SUMMARY:"))
    print(f"  • File:        {format_bold(disk_file)}" + (f" ➔ {new_name}" if new_name else ""))
    print(f"  • Source:      {src_cat} / {src_creator}")
    print(f"  • Destination: {format_green(dest_cat)} / {format_green(dest_creator)}")
    print(f"  • Base Root:   {reassign_core.BASE_DIR}")
    print("=" * 70)

    confirm = input("\nProceed with file move on disk and update catalog? (y/N): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("Move cancelled.")
        return

    try:
        res = reassign_core.move_file(
            source_cat=src_cat,
            source_creator=src_creator,
            file_display_name=file_name,
            dest_cat=dest_cat,
            dest_creator=dest_creator,
            new_file_name=new_name,
            move_companions=True
        )
        print(f"\n{format_green('✔ ' + res['message'])}")
        print(f"Moved on disk to: {res['destination']['creator']}")
        if res.get("companionCount", 0) > 0:
            print(f"Also moved {res['companionCount']} companion file(s).")
    except Exception as e:
        print(f"\n{format_red('✘ Move Failed:')} {e}")

def main():
    parser = argparse.ArgumentParser(description="Reassign and move 3D files to a different category/folder.")
    parser.add_argument("-f", "--file", help="File name (or archive name) to move")
    parser.add_argument("--from-cat", help="Source category (optional, autodetected if omitted)")
    parser.add_argument("--from-folder", help="Source folder/creator (optional, autodetected if omitted)")
    parser.add_argument("--to-cat", help="Destination category")
    parser.add_argument("--to-folder", help="Destination folder/creator")
    parser.add_argument("--new-name", help="New filename (optional rename)")
    parser.add_argument("--no-companions", action="store_true", help="Do not move companion multi-part or preview files")
    parser.add_argument("--undo", action="store_true", help="Undo the last move operation")
    parser.add_argument("-i", "--interactive", action="store_true", help="Launch interactive wizard")

    args = parser.parse_args()

    if args.undo:
        res = reassign_core.undo_last_move()
        if res.get("success"):
            print(format_green("✔ " + res.get("message", "Move undone.")))
        else:
            print(format_red("✘ Undo failed: " + res.get("message", "Unknown error.")))
        return

    # If no required arguments provided, run interactive mode
    if args.interactive or not (args.file and args.to_cat and args.to_folder):
        interactive_mode()
        return

    # CLI direct execution
    src_cat = args.from_cat
    src_folder = args.from_folder
    file_name = args.file

    # Autodetect source if not fully provided
    if not src_cat or not src_folder:
        lib_data = reassign_core.load_library_data()
        found = None
        for col in lib_data:
            for it in col.get("Items", []):
                clean_name, _ = reassign_core.clean_file_display_name(it.get("name", ""))
                if clean_name.lower() == file_name.lower() or it.get("name", "").lower() == file_name.lower():
                    if (not src_cat or col.get("Category", "").lower() == src_cat.lower()) and \
                       (not src_folder or col.get("Creator", "").lower() == src_folder.lower()):
                        found = (col.get("Category"), col.get("Creator"), it.get("name"))
                        break
            if found:
                break

        if found:
            src_cat, src_folder, file_name = found
        else:
            print(format_red(f"Error: Could not locate '{file_name}' in catalog. Please specify --from-cat and --from-folder."))
            sys.exit(1)

    try:
        res = reassign_core.move_file(
            source_cat=src_cat,
            source_creator=src_folder,
            file_display_name=file_name,
            dest_cat=args.to_cat,
            dest_creator=args.to_folder,
            new_file_name=args.new_name,
            move_companions=not args.no_companions
        )
        print(format_green("✔ " + res["message"]))
    except Exception as e:
        print(format_red("✘ Error: " + str(e)))
        sys.exit(1)

if __name__ == "__main__":
    main()
