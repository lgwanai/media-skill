import sentencepiece as spm
import sys

def main(bpe_path):
    sp = spm.SentencePieceProcessor(model_file=bpe_path)
    print(f"Vocab size: {sp.GetPieceSize()}")
    
    # Let's search for tags like [laughter], [breath], or any token starting with [
    special_tokens = []
    for i in range(sp.GetPieceSize()):
        piece = sp.IdToPiece(i)
        if piece.startswith('[') or piece.startswith('<') or 'laugh' in piece.lower() or 'breath' in piece.lower():
            special_tokens.append(piece)
            
    print("Found special tokens:")
    for t in special_tokens:
        print(t)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
