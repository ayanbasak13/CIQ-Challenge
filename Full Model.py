from __future__ import absolute_import, division

import re
import os
os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID";
 
os.environ["CUDA_VISIBLE_DEVICES"]="1"; 

import time
import numpy as np
import pandas as pd
import gensim
from tqdm import tqdm
from nltk.stem import PorterStemmer
ps = PorterStemmer()
from nltk.stem.lancaster import LancasterStemmer
lc = LancasterStemmer()
from nltk.stem import SnowballStemmer
sb = SnowballStemmer("english")
import gc

from keras.preprocessing.text import Tokenizer
from keras.preprocessing.sequence import pad_sequences
from keras.utils import to_categorical
from keras.layers import Dense, Input, LSTM, Embedding, Dropout, Activation, GRU, Conv1D
from keras.layers import Bidirectional, GlobalMaxPool1D, GlobalMaxPooling1D, GlobalAveragePooling1D
from keras.layers import Input, Embedding, Dense, Conv2D, MaxPool2D, concatenate
from keras.layers import Reshape, Flatten, Concatenate, Dropout, SpatialDropout1D
from keras.optimizers import Adam
from keras.models import Model
from keras import backend as K
from keras.engine.topology import Layer
from keras import initializers, regularizers, constraints, optimizers, layers

import sys
from os.path import dirname
#sys.path.append(dirname(dirname(__file__)))
from keras import initializers
from keras.engine import InputSpec, Layer
from keras import backend as K
import spacy

spell_model = gensim.models.KeyedVectors.load_word2vec_format('wiki-news-300d-1M/wiki-news-300d-1M.vec')
words = spell_model.index2word
w_rank = {}

for i,word in enumerate(words):
    w_rank[word] = i
    
WORDS = w_rank


# Use fast text as vocabulary
def words(text): 
    return re.findall(r'\w+', text.lower())


def P(word): 
    "Probability of `word`."
    # use inverse of rank as proxy
    # returns 0 if the word isn't in the dictionary
    return - WORDS.get(word, 0)


def correction(word): 
    "Most probable spelling correction for word."
    return max(candidates(word), key=P)


def candidates(word): 
    "Generate possible spelling corrections for word."
    return (known([word]) or known(edits1(word)) or [word])


def known(words): 
    "The subset of `words` that appear in the dictionary of WORDS."
    return set(w for w in words if w in WORDS)


def edits1(word):
    "All edits that are one edit away from `word`."
    letters    = 'abcdefghijklmnopqrstuvwxyz'
    splits     = [(word[:i], word[i:])    for i in range(len(word) + 1)]
    deletes    = [L + R[1:]               for L, R in splits if R]
    transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R)>1]
    replaces   = [L + c + R[1:]           for L, R in splits if R for c in letters]
    inserts    = [L + c + R               for L, R in splits for c in letters]
    return set(deletes + transposes + replaces + inserts)


def edits2(word): 
    "All edits that are two edits away from `word`."
    return (e2 for e1 in edits1(word) for e2 in edits1(e1))


def singlify(word):
    return "".join([letter for i,letter in enumerate(word) if i == 0 or letter != word[i-1]])


def load_glove(word_dict, lemma_dict):
    EMBEDDING_FILE = 'glove.840B.300d/glove.840B.300d.txt'
    def get_coefs(word,*arr): return word, np.asarray(arr, dtype='float32')
    embeddings_index = dict(get_coefs(*o.split(" ")) for o in open(EMBEDDING_FILE))
    embed_size = 300
    nb_words = len(word_dict)+1
    embedding_matrix = np.zeros((nb_words, embed_size), dtype=np.float32)
    unknown_vector = np.zeros((embed_size,), dtype=np.float32) - 1.
    print(unknown_vector[:5])
    for key in tqdm(word_dict):
        word = key
        embedding_vector = embeddings_index.get(word)
        if embedding_vector is not None:
            embedding_matrix[word_dict[key]] = embedding_vector
            continue
        word = key.lower()
        embedding_vector = embeddings_index.get(word)
        if embedding_vector is not None:
            embedding_matrix[word_dict[key]] = embedding_vector
            continue
        word = key.upper()
        embedding_vector = embeddings_index.get(word)
        if embedding_vector is not None:
            embedding_matrix[word_dict[key]] = embedding_vector
            continue
        word = key.capitalize()
        embedding_vector = embeddings_index.get(word)
        if embedding_vector is not None:
            embedding_matrix[word_dict[key]] = embedding_vector
            continue
        word = ps.stem(key)
        embedding_vector = embeddings_index.get(word)
        if embedding_vector is not None:
            embedding_matrix[word_dict[key]] = embedding_vector
            continue
        word = lc.stem(key)
        embedding_vector = embeddings_index.get(word)
        if embedding_vector is not None:
            embedding_matrix[word_dict[key]] = embedding_vector
            continue
        word = sb.stem(key)
        embedding_vector = embeddings_index.get(word)
        if embedding_vector is not None:
            embedding_matrix[word_dict[key]] = embedding_vector
            continue
        word = lemma_dict[key]
        embedding_vector = embeddings_index.get(word)
        if embedding_vector is not None:
            embedding_matrix[word_dict[key]] = embedding_vector
            continue
        if len(key) > 1:
            word = correction(key)
            embedding_vector = embeddings_index.get(word)
            if embedding_vector is not None:
                embedding_matrix[word_dict[key]] = embedding_vector
                continue
        embedding_matrix[word_dict[key]] = unknown_vector                    
    return embedding_matrix, nb_words 


def load_fasttext(word_dict, lemma_dict):
    EMBEDDING_FILE = 'wiki-news-300d-1M/wiki-news-300d-1M.vec'
    def get_coefs(word,*arr): return word, np.asarray(arr, dtype='float32')
    embeddings_index = dict(get_coefs(*o.split(" ")) for o in open(EMBEDDING_FILE) if len(o)>100)
    embed_size = 300
    nb_words = len(word_dict)+1
    embedding_matrix = np.zeros((nb_words, embed_size), dtype=np.float32)
    unknown_vector = np.zeros((embed_size,), dtype=np.float32) - 1.
    print(unknown_vector[:5])
    for key in tqdm(word_dict):
        word = key
        embedding_vector = embeddings_index.get(word)
        if embedding_vector is not None:
            embedding_matrix[word_dict[key]] = embedding_vector
            continue
        word = key.lower()
        embedding_vector = embeddings_index.get(word)
        if embedding_vector is not None:
            embedding_matrix[word_dict[key]] = embedding_vector
            continue
        word = key.upper()
        embedding_vector = embeddings_index.get(word)
        if embedding_vector is not None:
            embedding_matrix[word_dict[key]] = embedding_vector
            continue
        word = key.capitalize()
        embedding_vector = embeddings_index.get(word)
        if embedding_vector is not None:
            embedding_matrix[word_dict[key]] = embedding_vector
            continue
        word = ps.stem(key)
        embedding_vector = embeddings_index.get(word)
        if embedding_vector is not None:
            embedding_matrix[word_dict[key]] = embedding_vector
            continue
        word = lc.stem(key)
        embedding_vector = embeddings_index.get(word)
        if embedding_vector is not None:
            embedding_matrix[word_dict[key]] = embedding_vector
            continue
        word = sb.stem(key)
        embedding_vector = embeddings_index.get(word)
        if embedding_vector is not None:
            embedding_matrix[word_dict[key]] = embedding_vector
            continue
        word = lemma_dict[key]
        embedding_vector = embeddings_index.get(word)
        if embedding_vector is not None:
            embedding_matrix[word_dict[key]] = embedding_vector
            continue
        if len(key) > 1:
            word = correction(key)
            embedding_vector = embeddings_index.get(word)
            if embedding_vector is not None:
                embedding_matrix[word_dict[key]] = embedding_vector
                continue
        embedding_matrix[word_dict[key]] = unknown_vector                    
    return embedding_matrix, nb_words 


def load_para(word_dict, lemma_dict):
    EMBEDDING_FILE = 'paragram_300_sl999/paragram_300_sl999.txt'
    def get_coefs(word,*arr): return word, np.asarray(arr, dtype='float32')
    embeddings_index = dict(get_coefs(*o.split(" ")) for o in open(EMBEDDING_FILE, encoding="utf8", errors='ignore') if len(o)>100)
    embed_size = 300
    nb_words = len(word_dict)+1
    embedding_matrix = np.zeros((nb_words, embed_size), dtype=np.float32)
    unknown_vector = np.zeros((embed_size,), dtype=np.float32) - 1.
    print(unknown_vector[:5])
    for key in tqdm(word_dict):
        word = key
        embedding_vector = embeddings_index.get(word)
        if embedding_vector is not None:
            embedding_matrix[word_dict[key]] = embedding_vector
            continue
        word = key.lower()
        embedding_vector = embeddings_index.get(word)
        if embedding_vector is not None:
            embedding_matrix[word_dict[key]] = embedding_vector
            continue
        word = key.upper()
        embedding_vector = embeddings_index.get(word)
        if embedding_vector is not None:
            embedding_matrix[word_dict[key]] = embedding_vector
            continue
        word = key.capitalize()
        embedding_vector = embeddings_index.get(word)
        if embedding_vector is not None:
            embedding_matrix[word_dict[key]] = embedding_vector
            continue
        word = ps.stem(key)
        embedding_vector = embeddings_index.get(word)
        if embedding_vector is not None:
            embedding_matrix[word_dict[key]] = embedding_vector
            continue
        word = lc.stem(key)
        embedding_vector = embeddings_index.get(word)
        if embedding_vector is not None:
            embedding_matrix[word_dict[key]] = embedding_vector
            continue
        word = sb.stem(key)
        embedding_vector = embeddings_index.get(word)
        if embedding_vector is not None:
            embedding_matrix[word_dict[key]] = embedding_vector
            continue
        word = lemma_dict[key]
        embedding_vector = embeddings_index.get(word)
        if embedding_vector is not None:
            embedding_matrix[word_dict[key]] = embedding_vector
            continue
        if len(key) > 1:
            word = correction(key)
            embedding_vector = embeddings_index.get(word)
            if embedding_vector is not None:
                embedding_matrix[word_dict[key]] = embedding_vector
                continue
        embedding_matrix[word_dict[key]] = unknown_vector                    
    return embedding_matrix, nb_words


def build_model(embedding_matrix, nb_words, embedding_size=300):
    inp = Input(shape=(max_length,))
    x = Embedding(nb_words, embedding_size, weights=[embedding_matrix], trainable=False)(inp)
    x = SpatialDropout1D(0.3)(x)
    x1 = Bidirectional(LSTM(256, return_sequences=True))(x)
    x2 = Bidirectional(GRU(128, return_sequences=True))(x1)
    max_pool1 = GlobalMaxPooling1D()(x1)
    max_pool2 = GlobalMaxPooling1D()(x2)
    conc = Concatenate()([max_pool1, max_pool2])
    predictions = Dense(6, activation='softmax')(conc)
    model = Model(inputs=inp, outputs=predictions)
    adam = optimizers.Adam(lr=learning_rate)
    model.compile(optimizer=adam, loss='binary_crossentropy', metrics=['accuracy'])
    return model


train = pd.read_csv('ids_and_questions_dataset.csv')


train['Label'] = train['Label'].astype(str)
train = train.fillna(' ')
train = train.iloc[:,1:]

start_time = time.time()
print("Loading data ...")
# train = pd.read_csv('ids_and_questions_dataset.csv').fillna(' ')
# test = pd.read_csv('test.csv').fillna(' ')
train_text = train['Questions']
# test_text = test['question_text']
text_list = train_text
y1 = train['Label'].values
num_train_data = y1.shape[0]

# y = pd.get_dummies(train['Label']).values
#  print('Shape of label tensor:', y.shape)
# print("--- %s seconds ---" % (time.time() - start_time))

y = to_categorical(y1, num_classes=6)


start_time = time.time()
print("Spacy NLP ...")
nlp = spacy.load('en_core_web_lg', disable=['parser','ner','tagger'])
nlp.vocab.add_flag(lambda s: s.lower() in spacy.lang.en.stop_words.STOP_WORDS, spacy.attrs.IS_STOP)
word_dict = {}
word_index = 1
lemma_dict = {}
docs = nlp.pipe(text_list, n_threads = 2)

word_sequences = []

for doc in tqdm(docs):
    word_seq = []
    for token in doc:
        if (token.text not in word_dict) and (token.pos_ is not "PUNCT"):
            word_dict[token.text] = word_index
            word_index += 1
            lemma_dict[token.text] = token.lemma_
        if token.pos_ is not "PUNCT":
            word_seq.append(word_dict[token.text])
    word_sequences.append(word_seq)
del docs
gc.collect()
train_word_sequences = word_sequences[:num_train_data]
# test_word_sequences = word_sequences[num_train_data:]
print("--- %s seconds ---" % (time.time() - start_time))

# hyperparameters
max_length = 55
embedding_size = 600
learning_rate = 0.001
batch_size = 512
num_epoch = 20

train_word_sequences = pad_sequences(train_word_sequences, maxlen=max_length, padding='post')
# test_word_sequences = pad_sequences(test_word_sequences, maxlen=max_length, padding='post')
print(train_word_sequences[:1])
# print(test_word_sequences[:1])
# pred_prob = np.zeros((len(test_word_sequences),), dtype=np.float32)

start_time = time.time()
print("Loading embedding matrix ...")
embedding_matrix_glove, nb_words = load_glove(word_dict, lemma_dict)
embedding_matrix_fasttext, nb_words = load_fasttext(word_dict, lemma_dict)
embedding_matrix = np.concatenate((embedding_matrix_glove, embedding_matrix_fasttext), axis=1)
print("--- %s seconds ---" % (time.time() - start_time))

start_time = time.time()
print("Start training ...")
model = build_model(embedding_matrix, nb_words, embedding_size)
model.fit(train_word_sequences, y, batch_size=batch_size, epochs=num_epoch-1, verbose=2)
model.save("model_one.h5")
print("Saved model to disk")
# pred_prob += 0.15*np.squeeze(model.predict(test_word_sequences, batch_size=batch_size, verbose=2))
model.fit(train_word_sequences, y, batch_size=batch_size, epochs=1, verbose=2)
model.save("model_two.h5")
print("Saved model to disk")
# pred_prob += 0.35*np.squeeze(model.predict(test_word_sequences, batch_size=batch_size, verbose=2))
del model, embedding_matrix_fasttext, embedding_matrix
gc.collect()
K.clear_session()
print("--- %s seconds ---" % (time.time() - start_time))

start_time = time.time()
print("Loading embedding matrix ...")
embedding_matrix_para, nb_words = load_para(word_dict, lemma_dict)
embedding_matrix = np.concatenate((embedding_matrix_glove, embedding_matrix_para), axis=1)
print("--- %s seconds ---" % (time.time() - start_time))

start_time = time.time()
print("Start training ...")
model = build_model(embedding_matrix, nb_words, embedding_size)
model.fit(train_word_sequences, y, batch_size=batch_size, epochs=num_epoch-1, verbose=2)
model.save("model_three.h5")
print("Saved model to disk")
# pred_prob += 0.15*np.squeeze(model.predict(test_word_sequences, batch_size=batch_size, verbose=2))
model.fit(train_word_sequences, y, batch_size=batch_size, epochs=1, verbose=2)
model.save("model_four.h5")
print("Saved model to disk")
# pred_prob += 0.35*np.squeeze(model.predict(test_word_sequences, batch_size=batch_size, verbose=2))
print("--- %s seconds ---" % (time.time() - start_time))

'''submission = pd.DataFrame.from_dict({'qid': test['qid']})
submission['prediction'] = (pred_prob>0.35).astype(int)
submission.to_csv('submission.csv', index=False)'''

