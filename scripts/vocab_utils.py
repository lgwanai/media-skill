import re
import os
import yaml

def load_vocab(file_path):
    """
    Load vocabulary mapping from a YAML file.
    Expected format:
    Omini:
      - 欧米米
      - 欧米尼
      - o米你
    Returns a dict mapping from wrong_word to correct_word.
    e.g., {"欧米米": "Omini", "欧米尼": "Omini", "o米你": "Omini"}
    """
    if not os.path.exists(file_path):
        return {}
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            
        if not data:
            return {}
            
        vocab_map = {}
        for correct_word, wrong_words in data.items():
            if isinstance(wrong_words, list):
                for w in wrong_words:
                    vocab_map[str(w)] = str(correct_word)
            elif isinstance(wrong_words, str):
                vocab_map[wrong_words] = str(correct_word)
        return vocab_map
    except Exception as e:
        print(f"Warning: Failed to load hotwords file {file_path}: {e}")
        return {}

def tokenize(text):
    tokens = []
    matches = re.finditer(r'[a-zA-Z0-9]+|[^\s\w]|[\u4e00-\u9fa5]', text)
    for m in matches:
        token = m.group(0)
        if re.match(r'[，。、！？：；（）《》“”‘’"\'\.,!?;:\(\)\[\]-]', token):
            continue
        if token.strip():
            tokens.append(token)
    return tokens

def apply_vocab_to_sentence(text, timestamps, vocab):
    """
    Replace words in text and adjust timestamps accordingly.
    """
    if not vocab:
        return text, timestamps
        
    curr_text = text
    curr_ts = list(timestamps) if timestamps else []
    
    # Sort vocab by length of wrong word (descending) to match longest first
    sorted_vocab = sorted(vocab.items(), key=lambda x: len(x[0]), reverse=True)
    
    for old_word, new_word in sorted_vocab:
        # We need to process iteratively because replacing modifies the text and tokens
        while old_word in curr_text:
            if not curr_ts:
                # If no timestamps, just replace text
                curr_text = curr_text.replace(old_word, new_word, 1)
                continue
                
            tokens = tokenize(curr_text)
            
            if len(tokens) != len(curr_ts):
                # Fallback to just text replacement if mismatch
                curr_text = curr_text.replace(old_word, new_word, 1)
                continue
                
            old_tokens = tokenize(old_word)
            new_tokens = tokenize(new_word)
            
            if not old_tokens:
                break
                
            # Find the sequence of old_tokens in tokens
            seq_len = len(old_tokens)
            match_idx = -1
            for i in range(len(tokens) - seq_len + 1):
                if tokens[i:i+seq_len] == old_tokens:
                    match_idx = i
                    break
                    
            if match_idx == -1:
                # Text matched but tokens didn't
                curr_text = curr_text.replace(old_word, new_word, 1)
                continue
                
            # Perform replacement on text
            curr_text = curr_text.replace(old_word, new_word, 1)
            
            # Perform replacement on timestamps
            start_time = curr_ts[match_idx][0]
            end_time = curr_ts[match_idx + seq_len - 1][1]
            
            new_ts_segment = []
            duration = end_time - start_time
            num_new_tokens = len(new_tokens)
            
            if num_new_tokens > 0:
                step = duration / num_new_tokens
                for i in range(num_new_tokens):
                    seg_start = int(start_time + i * step)
                    seg_end = int(start_time + (i + 1) * step)
                    new_ts_segment.append([seg_start, seg_end])
                    
            curr_ts = curr_ts[:match_idx] + new_ts_segment + curr_ts[match_idx + seq_len:]
            
    return curr_text, curr_ts

def apply_vocab_to_result(res, vocab):
    """
    Apply vocabulary replacement to the entire FunASR result.
    """
    if not vocab or not res:
        return res
        
    for item in res:
        # Also replace in the raw text
        if "text" in item:
            for old_word, new_word in vocab.items():
                item["text"] = item["text"].replace(old_word, new_word)
                
        # Replace in sentence_info
        if "sentence_info" in item:
            for sentence in item["sentence_info"]:
                if "text" in sentence and "timestamp" in sentence:
                    new_text, new_ts = apply_vocab_to_sentence(
                        sentence["text"], 
                        sentence["timestamp"], 
                        vocab
                    )
                    sentence["text"] = new_text
                    sentence["timestamp"] = new_ts
                elif "text" in sentence:
                    for old_word, new_word in vocab.items():
                        sentence["text"] = sentence["text"].replace(old_word, new_word)
                        
    return res
