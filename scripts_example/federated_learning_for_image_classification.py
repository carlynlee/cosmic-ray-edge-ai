#!/usr/bin/env python
# coding: utf-8

# ##### Copyright 2019 The TensorFlow Authors.

# In[1]:


#@title Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# # Federated Learning for Image Classification

# <table class="tfo-notebook-buttons" align="left">
#   <td>
#     <a target="_blank" href="https://www.tensorflow.org/federated/tutorials/federated_learning_for_image_classification"><img src="https://www.tensorflow.org/images/tf_logo_32px.png" />View on TensorFlow.org</a>
#   </td>
#   <td>
#     <a target="_blank" href="https://colab.research.google.com/github/tensorflow/federated/blob/v0.86.0/docs/tutorials/federated_learning_for_image_classification.ipynb"><img src="https://www.tensorflow.org/images/colab_logo_32px.png" />Run in Google Colab</a>
#   </td>
#   <td>
#     <a target="_blank" href="https://github.com/tensorflow/federated/blob/v0.86.0/docs/tutorials/federated_learning_for_image_classification.ipynb"><img src="https://www.tensorflow.org/images/GitHub-Mark-32px.png" />View source on GitHub</a>
#   </td>
#   <td>
#     <a href="https://storage.googleapis.com/tensorflow_docs/federated/docs/tutorials/federated_learning_for_image_classification.ipynb"><img src="https://www.tensorflow.org/images/download_logo_32px.png" />Download notebook</a>
#   </td>
# </table>

# **NOTE**: This colab has been verified to work with the [latest released version](https://github.com/tensorflow/federated#compatibility) of the `tensorflow_federated` pip package, but the Tensorflow Federated project is still in pre-release development and may not work on `main`.
# 
# In this tutorial, we use the CREDO data in hit-images-final identified using a CNN (see: https://github.com/credo-ml/cnn-offline-trigger). Upload the zipped folder hit-images-final.zip to your google colab environment and run the script.
# 
# This tutorial, and the Federated Learning API, are intended primarily for users
# who want to plug their own TensorFlow models into TFF, treating the latter
# mostly as a black box. For a more in-depth understanding of TFF and how to
# implement your own federated learning algorithms, see the tutorials on the FC Core API - [Custom Federated Algorithms Part 1](custom_federated_algorithms_1.ipynb) and [Part 2](custom_federated_algorithms_2.ipynb).
# 
# For more on `tff.learning`, continue with the
# [Federated Learning for Text Generation](federated_learning_for_text_generation.ipynb),
# tutorial which in addition to covering recurrent models, also demonstrates loading a
# pre-trained serialized Keras model for refinement with federated learning
# combined with evaluation using Keras.

# ## Before we start
# 
# Before we start, please run the following to make sure that your environment is
# correctly setup. If you don't see a greeting, please refer to the
# [Installation](../install.md) guide for instructions.

# In[2]:


#@test {"skip": true}

get_ipython().system('pip install --quiet --upgrade tensorflow-federated')


# In[3]:


get_ipython().run_line_magic('load_ext', 'tensorboard')


# In[4]:


import collections

import numpy as np
import tensorflow as tf
import tensorflow_federated as tff

np.random.seed(0)

tff.federated_computation(lambda: 'Hello, World!')()


# In[5]:


get_ipython().system('pip install --quiet --upgrade unzip')
get_ipython().system('unzip -q hit-images-final.zip')


# Step 1: Load Local Image Data
# 

# In[6]:


import tensorflow as tf
import os
import collections
import numpy as np
import tensorflow_federated as tff

# Directory paths
data_dir = 'hit-images-final'  # Replace with your actual data directory

# Load dataset
def load_local_data(data_dir):
    dataset = tf.keras.preprocessing.image_dataset_from_directory(
        data_dir,
        image_size=(28, 28),  # Assuming your images are 28x28, adjust if needed
        color_mode='grayscale',
        batch_size=32,  # You can adjust this as needed
        label_mode='int'  # Ensures labels are returned as integers
    )
    return dataset

# Create a dataset from the local data
dataset = load_local_data(data_dir)


# Step 2: Preprocess the Dataset
# Modify the preprocessing function to match the format expected by TensorFlow Federated:

# In[7]:


NUM_CLIENTS = 10
NUM_EPOCHS = 5
BATCH_SIZE = 20
SHUFFLE_BUFFER = 100
PREFETCH_BUFFER = 10
def preprocess(dataset):

    def batch_format_fn(element, label):
        """Flatten a batch of `pixels` and return the features as an `OrderedDict`."""
        element = tf.reshape(element, [-1, 784])
        label = tf.reshape(label, [-1, 1])
        return collections.OrderedDict(x=element, y=label)

    return dataset.map(batch_format_fn).repeat(NUM_EPOCHS).shuffle(SHUFFLE_BUFFER, seed=1).batch(BATCH_SIZE).prefetch(PREFETCH_BUFFER)

preprocessed_dataset = preprocess(dataset)


# Step 3: Create Federated Data
# Since TFF expects client datasets, simulate this by dividing dataset into multiple subsets, each representing a client:

# In[8]:


def make_federated_data(dataset, num_clients):
    client_datasets = []
    dataset_size = len(dataset) // num_clients
    for i in range(num_clients):
        client_dataset = dataset.skip(i * dataset_size).take(dataset_size)
        client_datasets.append(preprocess(client_dataset))
    return client_datasets

federated_train_data = make_federated_data(dataset, NUM_CLIENTS)


# show label counts for some training data for each client
# 

# In[9]:


import numpy as np
from matplotlib import pyplot as plt
import collections

# Define the mapping of class numbers to class names
class_names = {
    0: 'artefacts',
    1: 'hits_votes_4_Dots',
    2: 'hits_votes_4_Lines',
    3: 'hits_votes_4_Worms'
}

# Number of examples per label for a sample of clients in the training data
f = plt.figure(figsize=(12, 7))
f.suptitle('Label Counts for a Sample of Clients (Training Data)')

for i in range(min(6, NUM_CLIENTS)):
    client_dataset = federated_train_data[i]
    plot_data = collections.defaultdict(list)

    for example in client_dataset:
        labels = example['y'].numpy().flatten()  # Assuming shape: (batch_size,)
        for label in labels:
            plot_data[label].append(label)

    plt.subplot(2, 3, i + 1)
    plt.title(f'Client {i}')

    for label in range(4):  # Assuming you have 4 labels: 0, 1, 2, 3
        plt.hist(
            plot_data[label],
            density=False,
            bins=np.arange(5) - 0.5,  # Ensures that bins are centered on integer labels
            label=class_names[label]
        )

    plt.xlabel('Label')
    plt.ylabel('Count')
    plt.legend()

plt.tight_layout()
plt.show()


# Plotting Mean Training Images Per Label for Clients

# In[10]:


import numpy as np
from matplotlib import pyplot as plt

# Define the mapping of class numbers to class names
class_names = {
    0: 'artefacts',
    1: 'hits_votes_4_Dots',
    2: 'hits_votes_4_Lines',
    3: 'hits_votes_4_Worms'
}

# Generate plots for the training data
for i in range(min(5, NUM_CLIENTS)):
    client_dataset = federated_train_data[i]
    plot_data = collections.defaultdict(list)

    for example in client_dataset:
        images = example['x'].numpy()  # shape: (batch_size, 32, 784)
        labels = example['y'].numpy().flatten()  # Assuming shape: (batch_size,)

        # Ensure correct association of images with labels
        for batch_idx in range(images.shape[0]):  # Iterate over the batch
            for img_idx in range(images.shape[1]):  # Iterate over images in the batch
                image = images[batch_idx, img_idx, :].reshape((28, 28))  # Reshape to 28x28
                label = labels[batch_idx]  # Get the correct label
                plot_data[label].append(image)  # Group images by label

    # Plot mean images for each label
    f = plt.figure(i, figsize=(12, 5))
    f.suptitle("Client #{}'s Mean Image Per Label (Training Data)".format(i))

    for j in range(4):  # Assuming you have 4 labels: 0, 1, 2, 3
        if plot_data[j]:  # Check if there are images for this label
            mean_img = np.mean(plot_data[j], axis=0)  # Calculate mean image

            plt.subplot(2, 2, j + 1)
            plt.imshow(mean_img, cmap='gray', aspect='equal')
            plt.title(class_names[j])  # Use class names for titles
            plt.axis('off')

    plt.show()


# Step 4: Train the Model
# With the local data loaded and processed, you can proceed with training the model using TensorFlow Federated as before:

# In[11]:


NUM_ROUNDS = 11
# Define the model function
def create_keras_model():
    return tf.keras.models.Sequential([
        tf.keras.layers.InputLayer(input_shape=(784,)),
        tf.keras.layers.Dense(10, kernel_initializer='zeros'),
        tf.keras.layers.Softmax(),
    ])

def model_fn():
    keras_model = create_keras_model()
    return tff.learning.models.from_keras_model(
        keras_model,
        input_spec=preprocessed_dataset.element_spec,
        loss=tf.keras.losses.SparseCategoricalCrossentropy(),
        metrics=[tf.keras.metrics.SparseCategoricalAccuracy()]
    )

# Build the training process
training_process = tff.learning.algorithms.build_weighted_fed_avg(
    model_fn,
    client_optimizer_fn=lambda: tf.keras.optimizers.SGD(learning_rate=0.02),
    server_optimizer_fn=lambda: tf.keras.optimizers.SGD(learning_rate=1.0)
)

# Initialize and train
train_state = training_process.initialize()

for round_num in range(1, NUM_ROUNDS):
    result = training_process.next(train_state, federated_train_data)
    train_state = result.state
    train_metrics = result.metrics
    print('round {:2d}, metrics={}'.format(round_num, train_metrics))


#  Load and Preprocess the Test Data
# test data is organized similarly to your training data (i.e., categorized by directories), so load and preprocess it in the same way.

# In[12]:


# Load test dataset
def load_test_data(test_data_dir):
    test_dataset = tf.keras.preprocessing.image_dataset_from_directory(
        test_data_dir,
        image_size=(28, 28),  # Assuming your images are 28x28, adjust if needed
        color_mode='grayscale',
        batch_size=32,
        label_mode='int'
    )
    return test_dataset

# Specify the path to your test dataset directory
test_data_dir = 'hit-images-final'

# Load and preprocess the test data
test_dataset = load_test_data(test_data_dir)
preprocessed_test_dataset = preprocess(test_dataset)


#  plot example images for one client

# In[13]:


from matplotlib import pyplot as plt

# Visualize example images for one client
figure = plt.figure(figsize=(20, 4))
j = 0

for example in preprocessed_test_dataset.take(1):  # Taking one batch for simplicity
    images = example['x'].numpy()  # shape: (20, 32, 784)

    # Flatten and reshape each image within the batch
    for batch_idx in range(images.shape[0]):  # Iterate over the batch
        for img_idx in range(images.shape[1]):  # Iterate over the 32 images within the batch
            if j >= 40:  # Stop if we've reached 40 images
                break
            image = images[batch_idx, img_idx, :].reshape((28, 28))  # Reshape to 28x28

            plt.subplot(4, 10, j + 1)
            plt.imshow(image, cmap='gray', aspect='equal')
            plt.axis('off')
            j += 1
        if j >= 40:
            break

plt.show()


# Create Federated Test Data
# As with the training data, create a federated version of your test data:

# In[14]:


federated_test_data = make_federated_data(test_dataset, NUM_CLIENTS)


# Evaluate the Model
# Use TensorFlow Federated evaluation process to evaluate the model on the federated test data:

# In[15]:


# Build the evaluation process
evaluation_process = tff.learning.algorithms.build_fed_eval(model_fn)

# Initialize the evaluation state
evaluation_state = evaluation_process.initialize()

# Set the model weights from the final trained state
model_weights = training_process.get_model_weights(train_state)
evaluation_state = evaluation_process.set_model_weights(evaluation_state, model_weights)

# Evaluate the model on the federated test data
evaluation_output = evaluation_process.next(evaluation_state, federated_test_data)

# Print the evaluation metrics
print('Evaluation metrics:', evaluation_output.metrics)


# ## Displaying model metrics in TensorBoard
# Next, let's visualize the metrics from these federated computations using Tensorboard.
# 
# Let's start by creating the directory and the corresponding summary writer to write the metrics to.
# 

# In[16]:


#@test {"skip": true}
logdir = "/tmp/logs/scalars/training/"
try:
  tf.io.gfile.rmtree(logdir)  # delete any previous results
except tf.errors.NotFoundError as e:
  pass # Ignore if the directory didn't previously exist.
summary_writer = tf.summary.create_file_writer(logdir)
train_state = training_process.initialize()


# Plot the relevant scalar metrics with the same summary writer.

# In[17]:


#@test {"skip": true}
with summary_writer.as_default():
  for round_num in range(1, NUM_ROUNDS):
    result = training_process.next(train_state, federated_train_data)
    train_state = result.state
    train_metrics = result.metrics
    for name, value in train_metrics['client_work']['train'].items():
      tf.summary.scalar(name, value, step=round_num)


# Start TensorBoard with the root log directory specified above. It can take a few seconds for the data to load.

# In[18]:


#@test {"skip": true}
get_ipython().system('ls {logdir}')
get_ipython().run_line_magic('tensorboard', '--logdir {logdir} --port=0')


# In[19]:


#@test {"skip": true}
# Uncomment and run this cell to clean your directory of old output for
# future graphs from this directory. We don't run it by default so that if
# you do a "Runtime > Run all" you don't lose your results.

# !rm -R /tmp/logs/scalars/*


# In order to view evaluation metrics the same way, you can create a separate eval folder, like "logs/scalars/eval", to write to TensorBoard.

# ## Customizing the model implementation
# 
# Keras is the [recommended high-level model API for TensorFlow](https://medium.com/tensorflow/standardizing-on-keras-guidance-on-high-level-apis-in-tensorflow-2-0-bad2b04c819a), and we encourage using Keras models (via
# `tff.learning.models.from_keras_model`) in TFF whenever possible.
# 
# However, `tff.learning` provides a lower-level model interface, `tff.learning.models.VariableModel`, that exposes the minimal functionality necessary for using a model for federated learning. Directly implementing this interface (possibly still using building blocks like `tf.keras.layers`) allows for maximum customization without modifying the internals of the federated learning algorithms.
# 
# So let's do it all over again from scratch.
# 
# ### Defining model variables, forward pass, and metrics
# 
# The first step is to identify the TensorFlow variables we're going to work with.
# In order to make the following code more legible, let's define a data structure
# to represent the entire set. This will include variables such as `weights` and
# `bias` that we will train, as well as variables that will hold various
# cumulative statistics and counters we will update during training, such as
# `loss_sum`, `accuracy_sum`, and `num_examples`.

# In[20]:


CredoVariables = collections.namedtuple(
    'CredoVariables', 'weights bias num_examples loss_sum accuracy_sum')


# Here's a method that creates the variables. For the sake of simplicity, we
# represent all statistics as `tf.float32`, as that will eliminate the need for
# type conversions at a later stage. Wrapping variable initializers as lambdas is
# a requirement imposed by
# [resource variables](https://www.tensorflow.org/api_docs/python/tf/enable_resource_variables).

# In[21]:


def create_credo_variables():
  return CredoVariables(
      weights=tf.Variable(
          lambda: tf.zeros(dtype=tf.float32, shape=(784, 10)),
          name='weights',
          trainable=True),
      bias=tf.Variable(
          lambda: tf.zeros(dtype=tf.float32, shape=(10)),
          name='bias',
          trainable=True),
      num_examples=tf.Variable(0.0, name='num_examples', trainable=False),
      loss_sum=tf.Variable(0.0, name='loss_sum', trainable=False),
      accuracy_sum=tf.Variable(0.0, name='accuracy_sum', trainable=False))


# With the variables for model parameters and cumulative statistics in place, we
# can now define the forward pass method that computes loss, emits predictions,
# and updates the cumulative statistics for a single batch of input data, as
# follows.

# In[22]:


def predict_on_batch(variables, x):
  return tf.nn.softmax(tf.matmul(x, variables.weights) + variables.bias)

def credo_forward_pass(variables, batch):
  y = predict_on_batch(variables, batch['x'])
  predictions = tf.cast(tf.argmax(y, 1), tf.int32)

  flat_labels = tf.reshape(batch['y'], [-1])
  loss = -tf.reduce_mean(
      tf.reduce_sum(tf.one_hot(flat_labels, 10) * tf.math.log(y), axis=[1]))
  accuracy = tf.reduce_mean(
      tf.cast(tf.equal(predictions, flat_labels), tf.float32))

  num_examples = tf.cast(tf.size(batch['y']), tf.float32)

  variables.num_examples.assign_add(num_examples)
  variables.loss_sum.assign_add(loss * num_examples)
  variables.accuracy_sum.assign_add(accuracy * num_examples)

  return loss, predictions


# Next, we define two functions that are related to local metrics, again using TensorFlow.
# 
# The first function `get_local_unfinalized_metrics` returns the unfinalized metric values (in addition to model updates, which are handled automatically) that are eligible to be aggregated to the server in a federated learning or evaluation process.

# In[23]:


def get_local_unfinalized_metrics(variables):
  return collections.OrderedDict(
      num_examples=[variables.num_examples],
      loss=[variables.loss_sum, variables.num_examples],
      accuracy=[variables.accuracy_sum, variables.num_examples])


# The second function `get_metric_finalizers` returns an `OrderedDict` of `tf.function`s with the same keys (i.e., metric names) as `get_local_unfinalized_metrics`. Each `tf.function` takes in the metric's unfinalized values and computes the finalized metric.

# In[24]:


def get_metric_finalizers():
  return collections.OrderedDict(
      num_examples=tf.function(func=lambda x: x[0]),
      loss=tf.function(func=lambda x: x[0] / x[1]),
      accuracy=tf.function(func=lambda x: x[0] / x[1]))


# How the local unfinalized metrics returned by `get_local_unfinalized_metrics` are aggregated across clients are specified by the `metrics_aggregator` parameter when defining the federated learning or evaluation processes. For example, in the [`tff.learning.algorithms.build_weighted_fed_avg`](https://www.tensorflow.org/federated/api_docs/python/tff/learning/algorithms/build_weighted_fed_avg) API (shown in the next section), the default value for `metrics_aggregator` is [`tff.learning.metrics.sum_then_finalize`](https://www.tensorflow.org/federated/api_docs/python/tff/learning/metrics/sum_then_finalize), which first sums the unfinalized metrics from `CLIENTS`, and then applies the metric finalizers at `SERVER`.

# ### Constructing an instance of `tff.learning.models.VariableModel`
# 
# With all of the above in place, we are ready to construct a model representation
# for use with TFF similar to one that's generated for you when you let TFF ingest
# a Keras model.

# In[25]:


import collections
from collections.abc import Callable

class CredoModel(tff.learning.models.VariableModel):

  def __init__(self):
    self._variables = create_credo_variables()

  @property
  def trainable_variables(self):
    return [self._variables.weights, self._variables.bias]

  @property
  def non_trainable_variables(self):
    return []

  @property
  def local_variables(self):
    return [
        self._variables.num_examples, self._variables.loss_sum,
        self._variables.accuracy_sum
    ]

  @property
  def input_spec(self):
    return collections.OrderedDict(
        x=tf.TensorSpec([None, 784], tf.float32),
        y=tf.TensorSpec([None, 1], tf.int32))

  @tf.function
  def predict_on_batch(self, x, training=True):
    del training
    return predict_on_batch(self._variables, x)

  @tf.function
  def forward_pass(self, batch, training=True):
    del training
    loss, predictions = credo_forward_pass(self._variables, batch)
    num_exmaples = tf.shape(batch['x'])[0]
    return tff.learning.models.BatchOutput(
        loss=loss, predictions=predictions, num_examples=num_exmaples)

  @tf.function
  def report_local_unfinalized_metrics(
      self) -> collections.OrderedDict[str, list[tf.Tensor]]:
    """Creates an `OrderedDict` of metric names to unfinalized values."""
    return get_local_unfinalized_metrics(self._variables)

  def metric_finalizers(
      self) -> collections.OrderedDict[str, Callable[[list[tf.Tensor]], tf.Tensor]]:
    """Creates an `OrderedDict` of metric names to finalizers."""
    return get_metric_finalizers()

  @tf.function
  def reset_metrics(self):
    """Resets metrics variables to initial value."""
    for var in self.local_variables:
      var.assign(tf.zeros_like(var))


# As you can see, the abstract methods and properties defined by
# `tff.learning.models.VariableModel` corresponds to the code snippets in the preceding section
# that introduced the variables and defined the loss and statistics.
# 
# Here are a few points worth highlighting:
# 
# *   All state that your model will use must be captured as TensorFlow variables,
#     as TFF does not use Python at runtime (remember your code should be written
#     such that it can be deployed to mobile devices; see the
#     [custom algorithms](custom_federated_algorithms_1.ipynb) tutorial for a more
#     in-depth commentary on the reasons).
# *   Your model should describe what form of data it accepts (`input_spec`), as
#     in general, TFF is a strongly-typed environment and wants to determine type
#     signatures for all components. Declaring the format of your model's input is
#     an essential part of it.
# *   Although technically not required, we recommend wrapping all TensorFlow
#     logic (forward pass, metric calculations, etc.) as `tf.function`s,
#     as this helps ensure the TensorFlow can be serialized, and removes the need
#     for explicit control dependencies.
# 

# The above is sufficient for evaluation and algorithms like Federated SGD.
# However, for Federated Averaging, we need to specify how the model should train
# locally on each batch. We will specify a local optimizer when building the Federated Averaging algorithm.

# ### Simulating federated training with the new model
# 
# With all the above in place, the remainder of the process looks like what we've
# seen already - just replace the model constructor with the constructor of our
# new model class, and use the two federated computations in the iterative process
# you created to cycle through training rounds.

# In[26]:


training_process = tff.learning.algorithms.build_weighted_fed_avg(
    CredoModel,
    client_optimizer_fn=lambda: tf.keras.optimizers.SGD(learning_rate=0.02))


# In[27]:


train_state = training_process.initialize()


# In[28]:


# Ensure the dataset is unbatched, processed, and then rebatch with correct shapes
def ensure_correct_shape(dataset):
    return dataset.unbatch().batch(1).map(lambda x: collections.OrderedDict(
        x=tf.reshape(x['x'], [-1, 784]),  # Flatten images to [?,784]
        y=tf.reshape(x['y'], [-1, 1])  # Ensure labels are [?,1]
    ))

# Apply the shape correction to the federated data
federated_train_data_corrected = [ensure_correct_shape(client_data) for client_data in federated_train_data]

# Now run the training step
result = training_process.next(train_state, federated_train_data_corrected)
train_state = result.state
metrics = result.metrics
print('round  1, metrics={}'.format(metrics))


# In[29]:


for round_num in range(2, 11):
    # Ensure the dataset for each client has the correct shape
    federated_train_data_corrected = [
        ensure_correct_shape(client_data) for client_data in federated_train_data
    ]

    result = training_process.next(train_state, federated_train_data_corrected)
    train_state = result.state
    metrics = result.metrics
    print('round {:2d}, metrics={}'.format(round_num, metrics))


# To see these metrics within TensorBoard, refer to the steps listed above in "Displaying model metrics in TensorBoard".

# ## Evaluation
# 
# All of our experiments so far presented only federated training metrics - the
# average metrics over all batches of data trained across all clients in the
# round. This introduces the normal concerns about overfitting, especially since
# we used the same set of clients on each round for simplicity, but there is an
# additional notion of overfitting in training metrics specific to the Federated
# Averaging algorithm. This is easiest to see if we imagine each client had a
# single batch of data, and we train on that batch for many iterations (epochs).
# In this case, the local model will quickly exactly fit to that one batch, and so
# the local accuracy metric we average will approach 1.0. Thus, these training
# metrics can be taken as a sign that training is progressing, but not much more.
# 
# To perform evaluation on federated data, you can construct another *federated
# computation* designed for just this purpose, using the
# `tff.learning.build_federated_evaluation` function, and passing in your model
# constructor as an argument. Note that unlike with Federated Averaging, where
# we've used `CredoTrainableModel`, it suffices to pass the `CredoModel`.
# Evaluation doesn't perform gradient descent, and there's no need to construct
# optimizers.
# 
# For experimentation and research, when a centralized test dataset is available,
# [Federated Learning for Text Generation](federated_learning_for_text_generation.ipynb)
# demonstrates another evaluation option: taking the trained weights from
# federated learning, applying them to a standard Keras model, and then simply
# calling `tf.keras.models.Model.evaluate()` on a centralized dataset.

# In[30]:


evaluation_process = tff.learning.algorithms.build_fed_eval(model_fn)


# You can inspect the abstract type signature of the evaluation function as follows.

# In[31]:


print(evaluation_process.next.type_signature.formatted_representation())


# Be aware that evaluation process is a `tff.lenaring.templates.LearningProcess` object. The object has an `initialize` method that will create the state, but this will contain an untrained model at first. Using the `set_model_weights` method, one must insert the weights from the training state to be evaluated.

# In[32]:


evaluation_state = evaluation_process.initialize()
model_weights = training_process.get_model_weights(train_state)
evaluation_state = evaluation_process.set_model_weights(evaluation_state, model_weights)


# Now with the evaluation state containing the model weights to be evaluated, we can compute evaluation metrics using evaluation datasets by calling the `next` method on the process, just like in training.
# 
# This will again return a `tff.learning.templates.LearingProcessOutput` instance.

# In[33]:


evaluation_output = evaluation_process.next(evaluation_state, federated_train_data)


# Here's what we get. Note the numbers look marginally better than what was
# reported by the last round of training above. By convention, the training
# metrics reported by the iterative training process generally reflect the
# performance of the model at the beginning of the training round, so the
# evaluation metrics will always be one step ahead.

# In[34]:


str(evaluation_output.metrics)


# Now, let's compile a test sample of federated data and rerun evaluation on the
# test data. The data will come from the same sample of real users, but from a
# distinct held-out data set.

# In[40]:


# Assuming test_dataset is a tf.data.Dataset and sample_clients is a list of client IDs
sample_clients = list(range(NUM_CLIENTS))

# Use the original tf.data.Dataset object without converting to a list
federated_test_data_v2 = make_federated_data(test_dataset, sample_clients)

# Check the length of the federated test data and inspect the first dataset
print(len(federated_test_data_v2), federated_test_data_v2[0])

len(federated_test_data), federated_test_data[0]


# In[ ]:


evaluation_output = evaluation_process.next(evaluation_state, federated_test_data)


# In[ ]:


str(evaluation_output.metrics)


# This concludes the tutorial. We encourage you to play with the
# parameters (e.g., batch sizes, number of users, epochs, learning rates, etc.), to modify the code above to simulate training on random samples of users in
# each round, and to explore the other tutorials we've developed.
