from . import LearningScheme
import tensorflow as tf
import numpy as np

class PolicyGradient(LearningScheme.LearningScheme):

    def __init__(self, window_inc=0, timeframe_size=100, **kwargs):
        super().__init__(**kwargs)

        # timeframe related
        self.learncount = 0
        self.framecount = 0
        self.timeframe_size = timeframe_size
        self.x = []
        self.score_gain = 0
        self.lastscore = 0
        self.lastcommand = [0.5,0.5,0.5]

        # inputs
        self.input_score_gain = tf.placeholder(tf.float32, shape=())
        self.input_window = self.architecture.getInputPlaceholder(timeframe_size)
        self.input = tf.squeeze(self.architecture.getInputPlaceholder(), axis=0)
        self.action_prob = self.architecture.createCalculation(self.input)
        self.output_keys = tf.squeeze(self.architecture.getOutputPlaceholder())

        # score-function for user-interaction
        self.score_fn_usr = tf.square(self.action_prob - self.output_keys)
        action_prob_tern = action_prob_tern(self.action_prob)
        if (not (action_prob_tern == self.output_keys).all()):
            self.update_usr = self.architecture.optimizer.minimize(self.score_fn_usr)

        # (POLICY GRADIENT) formulate score_fn_pg function
        score_fn_pg = tf.Variable(tf.zeros(kwargs["numkeys"]), name="score_fn_pg")
        for frame in range(timeframe_size):
            frame_prob = self.architecture.createCalculation(self.input_window[frame,:])
            score_fn_pg += self.input_score_gain*tf.log(frame_prob)
        self.score_fn_pg = score_fn_pg
        self.update_pg = self.optimizer.minimize(-self.score_fn_pg)

        # all variables set!
        super()._init__finished()
        self.sess.run(tf.global_variables_initializer())

    def action_prob_tern(self, action_prob):
        action_prob_tern = [0, 0]
        if (action_prob[0] > 1 / 3):
            action_prob_tern[0] = 1 / 2
        if (action_prob[0] > 2 / 3):
            action_prob_tern[0] = 1
        if (action_prob[1] > 1 / 2):
            action_prob_tern[1] = 1
        return action_prob_tern

    def _reset_pg(self):
        self.x = []
        self.framecount = 0

    def react(self, used_keys, image, absolute_score, userinput=False):

        # learn user commands
        if userinput:
            self.sess.run(self.update_usr, feed_dict={self.input: image, self.output_keys: used_keys})
            self._reset_pg()
            self.save()
            return used_keys # in case user is not giving input by the time of sending this message

        self.framecount += 1

        self.x.append(image)
        current_command = self.sess.run(self.action_prob, feed_dict={self.input: image}).reshape([-1])

        # learn policy gradient
        if self.timeframe_size == self.framecount:
            self.score_gain = absolute_score - self.lastscore - self.framecount/10
            self.sess.run(self.update_pg, feed_dict={self.input_window: self.x, self.input_score_gain: self.score_gain})
            print("\n\nLearning (Iteration:", self.learncount, ", ScoreGain:", self.score_gain ,")")
            self.learncount += 1
            self._reset_pg()
            self.lastscore = absolute_score
            self.save()

        return current_command.tolist()

    def game_restarted(self):
        self.x = []
        self.score_gain = []
