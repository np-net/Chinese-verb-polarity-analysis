# coding:utf-8

import os
import json
import argparse
from typing import List
from pyltp import SentenceSplitter

def split_tokens(sentence: str) -> List:
    if '[' not in sentence:
        return sentence.split('  ')
    # Otherwise, there are quoted NERs in the sentence

    # Find the span of first NER
    ner_start_pos = 0
    while ner_start_pos < len(sentence):
        if sentence[ner_start_pos] == '[':
            break
        ner_start_pos += 1
    ner_end_pos = ner_start_pos + 1
    bracket_lvl = 1
    while ner_end_pos < len(sentence):
        if sentence[ner_end_pos] == '[':
            bracket_lvl += 1
        if sentence[ner_end_pos] == ']':
            bracket_lvl -= 1
            if bracket_lvl == 0:
                break
        ner_end_pos += 1
    assert ner_end_pos < len(sentence)

    # Before first NER (we can safely split)
    before_content = sentence[:ner_start_pos].strip()
    before = before_content.split('  ') if before_content != '' else []
    # The NER part (there might be nested NERs)
    ner_part = split_tokens(sentence[ner_start_pos + 1: ner_end_pos])
    # Type label of the NER part and following tokens
    after_content = sentence[ner_end_pos + 1:]
    if '  ' in after_content:
        ner_lbl = after_content[:after_content.find('  ')]
        after = split_tokens(after_content[after_content.find('  ') + 2:])
    else:
        ner_lbl = after_content
        after = []
    return before + [(ner_part, ner_lbl)] + after


def process_tokens(tokens):
    words_list = []
    for index, token in enumerate(tokens):
        split_list = token.split('/')
        word, pos = split_list[0], split_list[1]
        words_list.append(word)

    for index, token in enumerate(tokens):
        split_list = token.split('/')
        word, pos = split_list[0], split_list[1]
        if pos == 'v':
            yield words_list, word, index

def fill_annotation(raw_path: str, anno_path:str) -> dict:
    raw_people_dict = read_file(raw_path)
    for file_name in os.listdir(anno_path):
        annotation = []
        with open(os.path.join(anno_path, file_name) + "\\{}.json".format(file_name), 'r', encoding='utf-8') as reader:
            json_data = json.load(reader)
            for anno in json_data:
                key = anno['key']
                label = anno['label']

                json_line = raw_people_dict[key]
                json_line['label'] = label

                annotation.append(json_line)

        with open(os.path.join(anno_path, file_name) + "\\{}.fill.json".format(file_name), 'w', encoding='utf-8') as writer:
            for anno in annotation:
                writer.write(json.dumps(anno, ensure_ascii=False) + '\n')



def read_file(path: str = '199801.txt') -> List[dict]:
    people_list = []
    skip_key = None
    page = 0
    with open(path, 'r', encoding='utf-8') as reader:
        for line in reader:
            line = line.strip()

            if len(line) == 0:
                page += 1

            key = line[:19].strip()
            sentence = line[22:].strip()
            tokens = []
            for token in split_tokens(sentence):
                if isinstance(token, str):
                    tokens.append(token)
                else:
                    tokens.extend(token[0])

            # 删除法律法规
            if key[-3:] == '001':
                if tokens[-1].split('/')[0] in ['法']:
                    skip_key = key[:-3]
                else:
                    skip_key = None
            if skip_key is not None and key.startswith(skip_key):
                continue

            # 只保留第一段
            if key[-3:] != '003':
                continue

            # 删除非完整句子
            if tokens[-1].split('/')[-1] != 'w' or (tokens[-1].split('/')[-1] == 'w'
                                                    and tokens[-1].split('/')[0] in ['）', '}', '】', '：', '，', '；', '”',
                                                                                     '》']):
                continue
            if tokens[0].split('/')[-1] == 'w' and tokens[0].split('/')[0] not in ['“', '（', '《']:
                continue

            try:
                for words_list, word, index in process_tokens(tokens):
                    phase = "".join(words_list)
                    sentence_list = SentenceSplitter.split(phase)
                    sentence_tokens_list = [[] for i in range(len(sentence_list))]

                    p = 0
                    for i in range(len(sentence_list)):
                        while ''.join(sentence_tokens_list[i]).strip() != sentence_list[i].strip():
                            sentence_tokens_list[i].append(words_list[p])
                            p += 1

                    for i in range(len(sentence_tokens_list)):
                        index -= len(sentence_tokens_list[i])
                        if index < 0:
                            index += len(sentence_tokens_list[i])
                            break

                    assert word == sentence_tokens_list[i][index]

                    people_list.append({
                        'key': "{}-{}".format(key, i),
                        'current_index': "{}-{}".format(key, len(people_list)),
                        'tokens': sentence_tokens_list[i],
                        'verb': word,
                        'token_index': [index]
                    })
            except:
                pass

    raw_text_dict = {}
    for people in people_list:
        people['key'] = people['current_index']
        del people['current_index']
        raw_text_dict[people['key']] = people

    return raw_text_dict


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Use PKU-released People\'s Daily corpus to fill rawtext of Chinese-verb-polarity-analysis dataset')
    parser.add_argument(
        '-r', '--raw', help='Filename of PKU released People\'s Daily corpus')
    parser.add_argument('-a', '--anno', default='Chinese-verb-polarity-analysis dataset-sample',
                        help='Root directory of annotation files')
    arguments = parser.parse_args()
    fill_annotation(arguments.raw, arguments.anno)
    print('Done')
