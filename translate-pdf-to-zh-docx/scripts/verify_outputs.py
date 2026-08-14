"""Validate translated .docx outputs and report corrupt / missing files.

Run after a batch translate to catch environment-induced corruption
(e.g. antivirus locking the file during write, producing a non-zip byte
stream). Prints a summary and exits non-zero if any problem is found.

Usage:
  verify_outputs.py <dir> [dir ...]
  (defaults to current directory)

Exit code: 0 if all outputs valid and complete, 1 otherwise.
"""
import os
import sys
import glob
import zipfile


def is_valid_doc(path):
    try:
        with zipfile.ZipFile(path) as z:
            return "word/document.xml" in z.namelist()
    except Exception:
        return False


def main():
    dirs = sys.argv[1:] or ["."]
    total = 0
    corrupt = []
    missing = []
    for d in dirs:
        if not os.path.isdir(d):
            print("skip (not a dir): %s" % d)
            continue
        pdfs = sorted(glob.glob(os.path.join(d, "*.pdf")))
        docs = sorted(glob.glob(os.path.join(d, "*-翻译.docx")))
        doc_base = {os.path.splitext(os.path.basename(x))[0].replace("-翻译", "")
                    for x in docs}
        for doc in docs:
            total += 1
            if not is_valid_doc(doc):
                corrupt.append(doc)
        for pdf in pdfs:
            base = os.path.splitext(os.path.basename(pdf))[0]
            if base not in doc_base:
                missing.append(pdf)
    print("=" * 50)
    print("doc outputs checked : %d" % total)
    print("corrupt (invalid)  : %d" % len(corrupt))
    print("PDFs missing transl: %d" % len(missing))
    print("=" * 50)
    for c in corrupt:
        print("  CORRUPT: %s" % os.path.basename(c))
    for m in missing:
        print("  MISSING: %s" % os.path.basename(m))
    if corrupt or missing:
        print("\nFix: delete the CORRUPT files, then re-run translate_pipeline.py "
              "on the folder (it skips existing valid outputs and only regenerates "
              "the bad/missing ones).")
        sys.exit(1)
    print("All outputs valid and complete.")


if __name__ == "__main__":
    main()
