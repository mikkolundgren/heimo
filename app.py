# encoding=iso-8859-1
import numpy as np
import pickle
import tensorflow as tf
from flask import Flask, jsonify, render_template, request, g
import model
import logging as log
import sqlite3
from datetime import datetime

log.basicConfig(filename='heimo.log', filemode='a', level=log.DEBUG,
                format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')


# Load in data structures
with open("data/wordlist.txt", "rb") as fp:
    wordList = fp.readlines()

wordList = [x.decode('iso-8859-1').strip() for x in wordList]


wordList.append('<pad>')
wordList.append('<EOS>')

# Load in hyperparamters
vocabSize = len(wordList)
batchSize = 24
maxEncoderLength = 15
maxDecoderLength = maxEncoderLength
lstmUnits = 112
embeddingDim = lstmUnits
numLayersLSTM = 3
numIterations = 500000

# Create placeholders
encoderInputs = [tf.placeholder(tf.int32, shape=(None,))
                 for i in range(maxEncoderLength)]
decoderLabels = [tf.placeholder(tf.int32, shape=(None,))
                 for i in range(maxDecoderLength)]
decoderInputs = [tf.placeholder(tf.int32, shape=(None,))
                 for i in range(maxDecoderLength)]
feedPrevious = tf.placeholder(tf.bool)

encoderLSTM = tf.nn.rnn_cell.BasicLSTMCell(lstmUnits, state_is_tuple=True)
#encoderLSTM = tf.nn.rnn_cell.MultiRNNCell([singleCell]*numLayersLSTM, state_is_tuple=True)
decoderOutputs, decoderFinalState = tf.contrib.legacy_seq2seq.embedding_rnn_seq2seq(encoderInputs, decoderInputs, encoderLSTM,
                                                                                    vocabSize, vocabSize, lstmUnits, feed_previous=feedPrevious)

decoderPrediction = tf.argmax(decoderOutputs, 2)

# Start session and get graph
sess = tf.Session()
#y, variables = model.getModel(encoderInputs, decoderLabels, decoderInputs, feedPrevious)

# Load in pretrained model
saver = tf.train.Saver()
saver.restore(sess, tf.train.latest_checkpoint('models'))
zeroVector = np.zeros((1), dtype='int32')

conn = sqlite3.connect('heimo.db')
conn.text_factory = lambda x: unicode(x, 'utf-8', 'ignore')


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect('heimo.db')
        db.text_factory = lambda x: unicode(x, 'iso-8859-1', 'ignore')
    return db


def init_db():
    c = conn.cursor()
    c.execute(
        '''CREATE TABLE IF NOT EXISTS chat_log (comment text, reply text, unix int)''')
    conn.commit()


def pred(inputString):
    log.info("got input message '%s' ", inputString)
    inputVector = model.getTestInput(inputString, wordList, maxEncoderLength)
    feedDict = {encoderInputs[t]: inputVector[t]
                for t in range(maxEncoderLength)}
    feedDict.update(
        {decoderLabels[t]: zeroVector for t in range(maxDecoderLength)})
    feedDict.update(
        {decoderInputs[t]: zeroVector for t in range(maxDecoderLength)})
    feedDict.update({feedPrevious: True})
    ids = (sess.run(decoderPrediction, feed_dict=feedDict))

    return model.idsToSentence(ids, wordList)


def save_to_db(conn, comment, response):
    c = conn.cursor()
    log.debug("inserting comment...")
    c.execute("INSERT INTO chat_log VALUES (?, ?, ?)",
              (comment, response, datetime.now()))
    conn.commit()


def read_logs(conn):
    c = conn.cursor()
    c.execute("SELECT comment, reply FROM chat_log order by unix DESC")
    return c.fetchall()


# webapp
app = Flask(__name__, template_folder='./')
with app.app_context():
    init_db()


@app.route('/prediction', methods=['POST', 'GET'])
def prediction():
    input = request.json['message']
    input = input.encode('iso-8859-1')
    response = pred(input)
    save_to_db(get_db(), input, response)
    return jsonify({"response": response})


@app.route('/logs', methods=['GET'])
def get_logs():
    result = read_logs(get_db())
    return jsonify(result)


@app.route('/')
def main():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
