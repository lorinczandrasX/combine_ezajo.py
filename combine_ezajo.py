import os
import sys

try:
    import pyperclip
except ImportError:
    print("-------------------------------------------------------------------")
    print("HIBA: A 'pyperclip' csomag nincs telepítve.")
    print("A vágólap használatához kérlek, telepítsd a következő paranccsal:")
    print("--> pip install pyperclip")
    print("-------------------------------------------------------------------")
    sys.exit(1)

# --- Konfiguráció ---
MAX_LINES = 5000
OUTPUT_PREFIX = "chunk"
ALLOWED_EXTENSIONS = {'.php', '.js', '.css', '.html', '.txt', '.md', '.json', '.xml'}
EXCLUDED_DIRS = {'__pycache__', '.git', '.vscode', 'node_modules', 'vendor'}

# --- Segítő kommentek ---
INTERMEDIATE_CHUNK_FOOTER = (
    "\n// --- FOLYTATÁS KÖVETKEZIK ---\n"
    "// A kódnak még nincs vége. Készen állok a következő rész (chunk) fogadására.\n"
)
FINAL_CHUNK_FOOTER = (
    "\n// --- EZ VOLT AZ UTOLSÓ RÉSZLET ---\n"
    "// Megkaptad a teljes kódot. Most kérlek, végezd el az elemzést a legelső üzenetben megfogalmazott kérésem alapján.\n"
)


def generate_directory_tree(root_dir, excluded_dirs_set, script_name):
    """Generál egy szöveges fa-struktúrát a megadott könyvtárról."""
    tree_lines = ["// --- PLUGIN FÁJLSZERKEZETE ---\n"]
    tree_lines.append(f"// {os.path.basename(os.path.abspath(root_dir))}/")

    for root, dirs, files in os.walk(root_dir, topdown=True):
        dirs[:] = [d for d in dirs if d not in excluded_dirs_set]
        
        files_to_render = sorted([
            f for f in files 
            if f != script_name 
            and not (f.startswith(f"{OUTPUT_PREFIX}_") and f.endswith(".txt"))
            and any(f.endswith(ext) for ext in ALLOWED_EXTENSIONS)
        ])
        dirs.sort()

        level = root.replace(root_dir, '').count(os.sep)
        indent = '    ' * level
        
        for d in dirs:
            tree_lines.append(f"// {indent}├── {d}/")
        
        for i, f in enumerate(files_to_render):
            prefix = '└──' if i == len(files_to_render) - 1 and not dirs else '├──'
            tree_lines.append(f"// {indent}{prefix} {f}")

    tree_lines.append("// ---------------------------\n\n")
    return "\n".join(tree_lines)


def create_chunks_in_current_dir():
    """
    Az aktuális könyvtárban fut. Ha a kód egy chunk-ba befér, vágólapra másolja.
    Ha nem, fájlokat hoz létre.
    """
    plugin_dir = '.'
    script_name = os.path.basename(__file__)
    
    print(f"Feldolgozás indul: '{os.path.abspath(plugin_dir)}'...")
    
    excluded_dirs_set = set(EXCLUDED_DIRS)
    directory_tree_str = generate_directory_tree(plugin_dir, excluded_dirs_set, script_name)

    all_files = []
    for root, dirs, files in os.walk(plugin_dir, topdown=True):
        dirs[:] = [d for d in dirs if d not in excluded_dirs_set]
        for file in sorted(files):
            is_script_itself = (file == script_name)
            is_previous_chunk = file.startswith(f"{OUTPUT_PREFIX}_") and file.endswith(".txt")
            
            if is_script_itself or is_previous_chunk:
                continue

            if any(file.endswith(ext) for ext in ALLOWED_EXTENSIONS):
                all_files.append(os.path.join(root, file))
    
    if not all_files:
        print("Hiba: Nem található egyetlen feldolgozható fájl sem a mappában.")
        return
        
    print(f"Összesen {len(all_files)} fájl feldolgozása...")

    all_chunks = []
    current_chunk_content = []
    lines_in_current_chunk = 0

    for file_path in all_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_lines = f.readlines()
            
            header = f"// --- {file_path.replace(os.sep, '/')} ---\n"
            # Hozzáadjuk a fejléc és az extra új sorok számát is
            lines_to_add = len(file_lines) + 3

            if lines_in_current_chunk > 0 and (lines_in_current_chunk + lines_to_add) > MAX_LINES:
                all_chunks.append(current_chunk_content)
                current_chunk_content = []
                lines_in_current_chunk = 0
            
            current_chunk_content.append(header)
            current_chunk_content.extend(file_lines)
            current_chunk_content.append("\n\n")
            lines_in_current_chunk += lines_to_add
        except Exception as e:
            print(f"Hiba a(z) '{file_path}' fájl olvasása közben: {e}")

    if current_chunk_content:
        all_chunks.append(current_chunk_content)

    if not all_chunks:
        print("Hiba: A feldolgozás során nem jött létre egyetlen chunk sem.")
        return
        
    total_chunks = len(all_chunks)

    # ÚJ: Döntés a kimenet alapján (vágólap vagy fájlok)
    if total_chunks == 1:
        # Ha csak egy chunk van, másolás vágólapra
        final_content_list = all_chunks[0]
        final_content_list.insert(0, directory_tree_str)
        final_content_list.append(FINAL_CHUNK_FOOTER)
        
        final_content_string = "".join(final_content_list)
        pyperclip.copy(final_content_string)
        
        print("\n------------------------------------------------------")
        print("SIKER: A kód elég rövid, ezért a vágólapra másoltam!")
        print("Most egyszerűen csak illeszd be (Ctrl+V).")
        print("------------------------------------------------------")
    else:
        # Ha több chunk van, fájlok létrehozása
        print(f"\nA kód túl hosszú, {total_chunks} darab fájl jön létre...")
        all_chunks[0].insert(0, directory_tree_str)

        for i, chunk_content in enumerate(all_chunks):
            is_last_chunk = (i + 1) == total_chunks
            
            if is_last_chunk:
                chunk_content.append(FINAL_CHUNK_FOOTER)
            else:
                chunk_content.append(INTERMEDIATE_CHUNK_FOOTER)
                
            output_filename = f"{OUTPUT_PREFIX}_{i + 1}.txt"
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.writelines(chunk_content)
            
            final_line_count = len("".join(chunk_content).splitlines())
            print(f"Létrehozva: {output_filename} ({final_line_count} sor)")
        
        print(f"\nFeldolgozás sikeresen befejezve.")


if __name__ == "__main__":
    create_chunks_in_current_dir()