import json
import os
import shutil
from typing import Dict, Any
import argh

def organize_pairs(
    jsonl_file: str,
    wav_src_dir: str,
    wav_dst_dir: str,
    txt_dst_dir: str,
    min_similarity: float = 0.6
) -> None:
    """
    Organize wav and txt files into separate folders based on JSONL comparison results.

    Args:
        jsonl_file: Path to input JSONL file with comparison results
        wav_src_dir: Source directory containing WAV files
        txt_src_dir: Source directory containing TXT files
        wav_dst_dir: Destination directory for selected WAV files
        txt_dst_dir: Destination directory for selected TXT files
        min_similarity: Minimum character similarity threshold (default: 0.7)
    """
    # Create destination directories if they don't exist
    os.makedirs(wav_dst_dir, exist_ok=True)
    os.makedirs(txt_dst_dir, exist_ok=True)

    copied_count = 0
    skipped_count = 0

    # Process JSONL file
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            result = json.loads(line)

            # Check similarity threshold
            if result.get('sim_char', 0) < min_similarity:
                skipped_count += 1
                continue

            wav_name = result['filename']
            txt_name = wav_name.replace('.wav', '.txt')

            # Source paths
            wav_src = os.path.join(wav_src_dir, wav_name)

            # Destination paths
            wav_dst = os.path.join(wav_dst_dir, wav_name)
            txt_dst = os.path.join(txt_dst_dir, txt_name)

            try:
                # Copy WAV file
                if os.path.exists(wav_src):
                    shutil.copy2(wav_src, wav_dst)
                else:
                    print(f"Warning: WAV file not found: {wav_src}")
                    continue

                # Write reference text to TXT file
                with open(txt_dst, 'w', encoding='utf-8') as txt_out:
                    txt_out.write(result['reference_text'])

                copied_count += 1
                print(f"Copied pair {copied_count}: {wav_name}")

            except Exception as e:
                print(f"Error processing {wav_name}: {str(e)}")
                skipped_count += 1

    print(f"\nProcessing complete:")
    print(f"Copied {copied_count} file pairs")
    print(f"Skipped {skipped_count} files")
    print(f"WAV files saved to: {wav_dst_dir}")
    print(f"TXT files saved to: {txt_dst_dir}")

if __name__ == "__main__":
    argh.dispatch_command(organize_pairs)
