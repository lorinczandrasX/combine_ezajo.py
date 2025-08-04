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
# A kizárási listában csupa kisbetűt használunk a következetességért
ALLOWED_EXTENSIONS = {'.php', '.js', '.css', '.html', '.txt', '.md', '.json', '.xml', '.scss'}
EXCLUDED_DIRS = {'__pycache__', '.git', '.vscode', 'node_modules', 'vendor', 'languages', 'build'}
EXCLUDED_FILES = {'package-lock.json', 'composer.lock'}

INTERMEDIATE_CHUNK_FOOTER = (
    "\n// --- FOLYTATÁS KÖVETKEZIK ---\n"
    "// A kódnak még nincs vége. Készen állok a következő rész (chunk) fogadására.\n"
)
FINAL_CHUNK_FOOTER = (
    "\n// --- EZ VOLT AZ UTOLSÓ RÉSZLET ---\n"
    "// Megkaptad a teljes kódot. Most kérlek, végezd el az elemzést a legelső üzenetben megfogalmazott kérésem alapján.\n"
)

def generate_directory_tree(root_dir, excluded_dirs_set, script_name):
    tree_lines = ["// --- PLUGIN FÁJLSZERKEZETE ---\n"]
    tree_lines.append(f"// {os.path.basename(os.path.abspath(root_dir))}/")

    def build_tree_recursive(current_dir, prefix=""):
        try:
            items = sorted(os.listdir(current_dir))
        except OSError:
            return

        # JAVÍTÁS: A mappa nevének kisbetűs változatát hasonlítjuk össze a kizárási listával
        dirs = [d for d in items if os.path.isdir(os.path.join(current_dir, d)) and d.lower() not in excluded_dirs_set]
        files = [
            f for f in items
            if os.path.isfile(os.path.join(current_dir, f))
            and f != script_name
            and not (f.startswith(OUTPUT_PREFIX + '_') and f.endswith('.txt'))
            and any(f.endswith(ext) for ext in ALLOWED_EXTENSIONS)
            and f not in EXCLUDED_FILES
        ]

        entries = dirs + files

        for i, entry in enumerate(entries):
            connector = "└── " if i == len(entries) - 1 else "├── "
            tree_lines.append(f"// {prefix}{connector}{entry}")
            if entry in dirs:
                extension = "│   " if i < len(entries) - 1 else "    "
                build_tree_recursive(os.path.join(current_dir, entry), prefix + extension)

    build_tree_recursive(root_dir)
    tree_lines.append("// ---------------------------\n\n")
    return "\n".join(tree_lines)

def create_chunks_in_current_dir():
    plugin_dir = '.'
    script_name = os.path.basename(__file__)
    print(f"Feldolgozás indul: '{os.path.abspath(plugin_dir)}'...")

    # JAVÍTÁS: A kizárási listát eleve kisbetűs elemekkel hozzuk létre
    excluded_dirs_set = {d.lower() for d in EXCLUDED_DIRS}
    directory_tree_str = generate_directory_tree(plugin_dir, excluded_dirs_set, script_name)

    all_files = []
    for root, dirs, files in os.walk(plugin_dir, topdown=True):
        # JAVÍTÁS: A mappák nevének kisbetűs változatát hasonlítjuk össze
        dirs[:] = [d for d in dirs if d.lower() not in excluded_dirs_set]
        
        for file in sorted(files):
            is_script_itself = (file == script_name)
            is_previous_chunk = file.startswith(f"{OUTPUT_PREFIX}_") and file.endswith(".txt")
            if is_script_itself or is_previous_chunk or file in EXCLUDED_FILES:
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
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                file_lines = f.readlines()
            header = f"// --- {file_path.replace(os.sep, '/')} ---\n"
            lines_to_add = len(file_lines) + 3
            if lines_in_current_chunk > 0 and (lines_in_current_chunk + lines_to_add) > MAX_LINES:
                all_chunks.append("".join(current_chunk_content))
                current_chunk_content = []
                lines_in_current_chunk = 0
            
            if not current_chunk_content:
                # Az első chunk-ba beletesszük a fastruktúrát
                if not all_chunks: 
                    current_chunk_content.append(directory_tree_str)
                    lines_in_current_chunk += len(directory_tree_str.splitlines())

            current_chunk_content.append(header)
            current_chunk_content.extend(file_lines)
            current_chunk_content.append("\n\n")
            lines_in_current_chunk += lines_to_add
        except Exception as e:
            print(f"Hiba a(z) '{file_path}' fájl olvasása közben: {e}")

    if current_chunk_content:
        all_chunks.append("".join(current_chunk_content))

    if not all_chunks:
        print("Hiba: A feldolgozás során nem jött létre egyetlen chunk sem.")
        return

    total_chunks = len(all_chunks)

    # A régi logikát felváltja egy egyszerűbb, ami a chunkok tartalmát kezeli
    # és nem listákat ad át, hanem már összeállított stringeket.
    if total_chunks == 1:
        final_content = all_chunks[0] + FINAL_CHUNK_FOOTER
        pyperclip.copy(final_content)
        print("\n------------------------------------------------------")
        print("SIKER: A kód elég rövid, ezért a vágólapra másoltam!")
        print("Most egyszerűen csak illeszd be (Ctrl+V).")
        print("------------------------------------------------------")
    else:
        print(f"\nA kód túl hosszú, {total_chunks} darab fájl jön létre...")
        for i, chunk_str in enumerate(all_chunks):
            is_last_chunk = (i + 1) == total_chunks
            
            final_chunk_content = chunk_str
            if is_last_chunk:
                final_chunk_content += FINAL_CHUNK_FOOTER
            else:
                final_chunk_content += INTERMEDIATE_CHUNK_FOOTER

            output_filename = f"{OUTPUT_PREFIX}_{i + 1}.txt"
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(final_chunk_content)
            
            final_line_count = len(final_chunk_content.splitlines())
            print(f"Létrehozva: {output_filename} ({final_line_count} sor)")
        
        print(f"\nFeldolgozás sikeresen befejezve.")

if __name__ == "__main__":
    create_chunks_in_current_dir()