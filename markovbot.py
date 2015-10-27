#! /usr/bin/python

####### My First IRC Bot #######
#
# Following along from a blog post from eflorenzano.com and adding some personal flavour,
# this code is for a Markov-Chain IRC Bot using Twisted and Python
#
# Using code from http://eflorenzano.com/blog/2008/11/17/writing-markov-chain-irc-bot-twisted-and-python/
#
# Authored by Ryan Hawker on 10/16/2015
#
################################

from twisted.words.protocols import irc
from twisted.internet import protocol, reactor
from collections import defaultdict
import re
import random
import sys
import os

markov = defaultdict(list)
STOP_WORD = "\n"

# This function takes the word after each n-word sliding window and appends it to the list of possible words
def add_to_brain(msg, chain_length, write_to_file=False):
    if write_to_file:
        f = open('training_text.txt', 'a')
        f.write(msg + '\n')
        f.close()
    buf = [STOP_WORD] * chain_length
    for word in msg.split():
        markov[tuple(buf)].append(word)
        del buf[0]
        buf.append(word)
    markov[tuple(buf)].append(STOP_WORD)

# This function generates sentences from our brain that we made above
# We basically mimic the start of our received message, and then populate the rest
# with random words from the brain. If we catch a STOP_WORD, we return the sentence.
def generate_sentence(msg, chain_length, max_words=10000):
    buf = msg.split()[:chain_length] # Not sure what this is doing..
    if len(msg.split()) > chain_length:
        message = buf[:]
    else:
        message = []
        for i in xrange(chain_length):
            message.append(random.choice(markov[random.choice(markov.keys())]))
    for i in xrange(max_words):
        try:
            next_word = random.choice(markov[tuple(buf)])
        except IndexError:
            continue
        if next_word == STOP_WORD:
            break
        message.append(next_word)
        del buf[0]
        buf.append(next_word)
    return ' '.join(message)

class MarkovBot(irc.IRCClient):

    def _get_nickname(self):
        return self.factory.nickname
    nickname = property(_get_nickname)

    def signedOn(self):
        self.join(self.factory.channel)
        print "Signed on as %s." % (self.nickname,)

    def joined(self, channel):
        print "Joined %s." % (channel,)

    def privmsg(self, user, channel, msg):
        if not user:
            return
        if self.nickname in msg:
            msg = re.compile(self.nickname + "[:,]* ?", re.I).sub('', msg)
            prefix = "%s: " % (user.split('!', 1)[0], )
        else:
            print "no name so here I am"
            prefix = ' '
        add_to_brain(msg, self.factory.chain_length, write_to_file=True)
        if prefix or random.random() <= self.factory.chattiness:
            print "generating a sentence"
            sentence = generate_sentence(msg, self.factory.chain_length, self.factory.max_words)
            print sentence
            if sentence:
                self.msg(self.factory.channel, prefix + sentence)
        #print msg

class MarkovBotFactory(protocol.ClientFactory):
    protocol = MarkovBot

    def __init__(self, channel, nickname='MarkTheBot', chain_length=3, chattiness=1.0, max_words=10000):
        self.channel = channel
        self.nickname = nickname
        self.chain_length = chain_length
        self.chattiness = chattiness
        self.max_words = max_words

    def clientConnectionlost(self, connector, reason):
        print "Lost connection (%s), reconnecting." % (reason,)
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "Could not connect: %s" % (reason,)


if __name__ == "__main__":
    try:
        chan = sys.argv[1]
    except IndexError:
        print "Please specify a channel name!"
    if os.path.exists('training_text.txt'):
        f = open('training_text.txt', 'r')
        for line in f:
            add_to_brain(line, 20) #Chain length 20 wasn't accepting chain_length variable 
        print 'Brain reloaded'
        f.close()

    reactor.connectTCP('irc.freenode.net', 6667, MarkovBotFactory('#' + chan, 'MarkTheBot', 20, chattiness=0.56))
    reactor.run()

