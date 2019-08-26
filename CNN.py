#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Author:Speciallan

'''
代码实现了LeNet网络，并完成了手写数字数据集MNIST的训练。
'''

# 先对MNIST数据集进行读入以及处理
# 数据从MNIST官网直接下载
import numpy as np
import matplotlib.pyplot as plt
from struct import unpack


def read_image(path):
    with open(path, 'rb') as f:
        magic, num, rows, cols = unpack('>4I', f.read(16))
        img = np.fromfile(f, dtype=np.uint8).reshape(num, rows, cols, 1)  # 将图片格式进行规定，加上通道数
    return img


def read_label(path):
    with open(path, 'rb') as f:
        magic, num = unpack('>2I', f.read(8))
        label = np.fromfile(f, dtype=np.uint8)
    return label


def normalize_image(image):
    img = image.astype(np.float32) / 255.0
    return img


def one_hot_label(label):
    lab = np.zeros((label.size, 10))
    for i, row in enumerate(lab):
        row[label[i]] = 1
    return lab


def padding(image, zero_num):
    if len(image.shape) == 4:
        image_padding = np.zeros(
            (image.shape[0], image.shape[1] + 2 * zero_num, image.shape[2] + 2 * zero_num, image.shape[3]))
        image_padding[:, zero_num:image.shape[1] + zero_num, zero_num:image.shape[2] + zero_num, :] = image
    elif len(image.shape) == 3:
        image_padding = np.zeros((image.shape[0] + 2 * zero_num, image.shape[1] + 2 * zero_num, image.shape[2]))
        image_padding[zero_num:image.shape[0] + zero_num, zero_num:image.shape[1] + zero_num, :] = image
    else:
        print("维度错误")
        sys.exit()
    return image_padding


# 加载数据集以及数据预处理

def dataset_loader():
    path = '/home/speciallan/Documents/python/data/MNIST/'
    train_image = read_image(path + 'train-images-idx3-ubyte')
    train_label = read_label(path + 'train-labels-idx1-ubyte')
    test_image = read_image(path + 't10k-images-idx3-ubyte')
    test_label = read_label(path + 't10k-labels-idx1-ubyte')

    train_image = normalize_image(train_image)
    train_label = one_hot_label(train_label)
    train_label = train_label.reshape(train_label.shape[0], train_label.shape[1], 1)

    test_image = normalize_image(test_image)
    test_label = one_hot_label(test_label)
    test_label = test_label.reshape(test_label.shape[0], test_label.shape[1], 1)

    train_image = padding(train_image, 2)  # 对初始图像进行零填充，保证与LeNet输入结构一致60000*32*32*1
    test_image = padding(test_image, 2)

    return train_image, train_label, test_image, test_label


def conv(img, conv_filter):
    if len(img.shape) != 3 or len(conv_filter.shape) != 4:
        print("卷积运算所输入的维度不符合要求")
        sys.exit()

    if img.shape[-1] != conv_filter.shape[-1]:
        print("卷积输入图片与卷积核的通道数不一致")
        sys.exit()

    img_h, img_w, img_ch = img.shape
    filter_num, filter_h, filter_w, img_ch = conv_filter.shape
    feature_h = img_h - filter_h + 1
    feature_w = img_w - filter_w + 1

    # 初始化输出的特征图片，由于没有使用零填充，图片尺寸会减小
    img_out = np.zeros((feature_h, feature_w, filter_num))
    img_matrix = np.zeros((feature_h * feature_w, filter_h * filter_w * img_ch))
    filter_matrix = np.zeros((filter_h * filter_w * img_ch, filter_num))

    # 将输入图片张量转换成矩阵形式
    for i in range(feature_h * feature_w):
        for j in range(img_ch):
            img_matrix[i, j * filter_h * filter_w:(j + 1) * filter_h * filter_w] = \
                img[np.uint16(i / feature_w):np.uint16(i / feature_w + filter_h),
                np.uint16(i % feature_w):np.uint16(i % feature_w + filter_w), j].reshape(filter_h * filter_w)

    # 将卷积核张量转换成矩阵形式
    for i in range(filter_num):
        filter_matrix[:, i] = conv_filter[i, :].reshape(filter_w * filter_h * img_ch)

    feature_matrix = np.dot(img_matrix, filter_matrix)

    # 将以矩阵形式存储的卷积结果再转换为张量形式
    for i in range(filter_num):
        img_out[:, :, i] = feature_matrix[:, i].reshape(feature_h, feature_w)

    return img_out


def conv_(img, conv_filter):
    # 对二维图像以及二维卷积核进行卷积，不填充
    img_h, img_w = img.shape
    filter_h, filter_w = conv_filter.shape
    feature_h = img_h - filter_h + 1
    feature_w = img_w - filter_w + 1

    img_matrix = np.zeros((feature_h * feature_w, filter_h * filter_w))
    for i in range(feature_h * feature_w):
        img_matrix[i:] = img[np.uint16(i / feature_w):np.uint16(i / feature_w + filter_h),
                         np.uint16(i % feature_w):np.uint16(i % feature_w + filter_w)].reshape(filter_w * filter_h)
    filter_matrix = conv_filter.reshape(filter_h * filter_w, 1)

    img_out = np.dot(img_matrix, filter_matrix)

    img_out = img_out.reshape(feature_h, feature_w)

    return img_out


def conv_cal_w(out_img_delta, in_img):
    # 由卷积前的图片以及卷积后的delta计算卷积核的梯度
    nabla_conv = np.zeros([out_img_delta.shape[-1], in_img.shape[0] - out_img_delta.shape[0] + 1,
                           in_img.shape[1] - out_img_delta.shape[1] + 1, in_img.shape[-1]])
    for filter_num in range(nabla_conv.shape[0]):
        for ch_num in range(nabla_conv.shape[-1]):
            nabla_conv[filter_num, :, :, ch_num] = conv_(in_img[:, :, ch_num], out_img_delta[:, :, filter_num])
    return nabla_conv


def conv_cal_b(out_img_delta):
    nabla_b = np.zeros((out_img_delta.shape[-1], 1))
    for i in range(out_img_delta.shape[-1]):
        nabla_b[i] = np.sum(out_img_delta[:, :, i])
    return nabla_b


def relu(feature):
    '''Relu激活函数，有两种情况会使用到
    当在卷积层中使用时，feature为一个三维张量，，[行，列，通道]
    当在全连接层中使用时，feature为一个列向量'''
    relu_out = np.zeros(feature.shape)

    if len(feature.shape) > 2:
        for ch_num in range(feature.shape[-1]):
            for r in range(feature.shape[0]):
                for c in range(feature.shape[1]):
                    relu_out[r, c, ch_num] = max(feature[r, c, ch_num], 0)
    else:
        for r in range(feature.shape[0]):
            relu_out[r, 0] = max(feature[r, 0], 0)
    return relu_out


def relu_prime(feature):  # 对relu函数的求导
    '''relu函数的一阶导数，间断点导数认为是0'''

    relu_prime_out = np.zeros(feature.shape)

    if len(feature.shape) > 2:
        for ch_num in range(feature.shape[-1]):
            for r in range(feature.shape[0]):
                for c in range(feature.shape[1]):
                    if feature[r, c, ch_num] > 0:
                        relu_prime_out[r, c, ch_num] = 1

    else:
        for r in range(feature.shape[0]):
            if feature[r, 0] > 0:
                relu_prime_out[r, 0] = 1

    return relu_prime_out


def pool(feature, size=2, stride=2):
    '''最大池化操作
    同时输出池化后的结果以及用于记录最大位置的张量，方便之后delta误差反向传播'''
    pool_out = np.zeros([np.uint16((feature.shape[0] - size) / stride + 1),
                         np.uint16((feature.shape[1] - size) / stride + 1),
                         feature.shape[2]])
    pool_out_max_location = np.zeros(pool_out.shape)  # 该函数用于记录最大值位置
    for ch_num in range(feature.shape[-1]):
        r_out = 0
        for r in np.arange(0, feature.shape[0] - size + 1, stride):
            c_out = 0
            for c in np.arange(0, feature.shape[1] - size + 1, stride):
                pool_out[r_out, c_out, ch_num] = np.max(feature[r:r + size, c:c + size, ch_num])
                pool_out_max_location[r_out, c_out, ch_num] = np.argmax(
                    feature[r:r + size, c:c + size, ch_num])  # 记录最大点位置
                c_out += 1
            r_out += 1
    return pool_out, pool_out_max_location


def pool_delta_error_bp(pool_out_delta, pool_out_max_location, size=2, stride=2):
    delta = np.zeros([np.uint16((pool_out_delta.shape[0] - 1) * stride + size),
                      np.uint16((pool_out_delta.shape[1] - 1) * stride + size),
                      pool_out_delta.shape[2]])
    for ch_num in range(pool_out_delta.shape[-1]):
        for r in range(pool_out_delta.shape[0]):
            for c in range(pool_out_delta.shape[1]):
                order = pool_out_max_location[r, c, ch_num]
                m = np.uint16(stride * r + order // size)
                n = np.uint16(stride * c + order % size)
                delta[m, n, ch_num] = pool_out_delta[r, c, ch_num]
    return delta


def rot180(conv_filters):
    rot180_filters = np.zeros((conv_filters.shape))
    for filter_num in range(conv_filters.shape[0]):
        for img_ch in range(conv_filters.shape[-1]):
            rot180_filters[filter_num, :, :, img_ch] = np.flipud(np.fliplr(conv_filters[filter_num, :, :, img_ch]))
    return rot180_filters


def soft_max(z):
    tmp = np.max(z)
    z -= tmp  # 用于缩放每行的元素，避免溢出，有效
    z = np.exp(z)
    tmp = np.sum(z)
    z /= tmp

    return z


def add_bias(conv, bias):
    if conv.shape[-1] != bias.shape[0]:
        print("给卷积添加偏置维度出错")
    else:
        for i in range(bias.shape[0]):
            conv[:, :, i] += bias[i, 0]
    return conv


# In[32]:


class ConvNet(object):

    def __init__(self):

        '''
        2层卷积，2层池化，3层全连接'''
        self.filters = [np.random.randn(6, 5, 5, 1)]  # 图像变成 28*28*6 池化后图像变成14*14*6
        self.filters_biases = [np.random.randn(6, 1)]
        self.filters.append(np.random.randn(16, 5, 5, 6))  # 图像变成 10*10*16 池化后变成5*5*16
        self.filters_biases.append(np.random.randn(16, 1))

        self.weights = [np.random.randn(120, 400)]
        self.weights.append(np.random.randn(84, 120))
        self.weights.append(np.random.randn(10, 84))
        self.biases = [np.random.randn(120, 1)]
        self.biases.append(np.random.randn(84, 1))
        self.biases.append(np.random.randn(10, 1))

    def feed_forward(self, x):
        # 第一层卷积
        conv1 = add_bias(conv(x, self.filters[0]), self.filters_biases[0])
        relu1 = relu(conv1)
        pool1, pool1_max_locate = pool(relu1)

        # 第二层卷积
        conv2 = add_bias(conv(pool1, self.filters[1]), self.filters_biases[1])
        relu2 = relu(conv2)
        pool2, pool2_max_locate = pool(relu2)

        # 拉直
        straight_input = pool2.reshape(pool2.shape[0] * pool2.shape[1] * pool2.shape[2], 1)

        # 第一层全连接
        full_connect1_z = np.dot(self.weights[0], straight_input) + self.biases[0]
        full_connect1_a = relu(full_connect1_z)

        # 第二层全连接
        full_connect2_z = np.dot(self.weights[1], full_connect1_a) + self.biases[1]
        full_connect2_a = relu(full_connect2_z)

        # 第三层全连接（输出）
        full_connect3_z = np.dot(self.weights[2], full_connect2_a) + self.biases[2]
        full_connect3_a = soft_max(full_connect3_z)
        return full_connect3_a

    def evaluate(self, images, labels):
        result = 0
        for img, lab in zip(images, labels):
            predict_label = self.feed_forward(img)
            if np.argmax(predict_label) == np.argmax(lab):
                result += 1
        return result

    def SGD(self, train_image, train_label, test_image, test_label, epochs, mini_batch_size, eta):
        '''Stochastic gradiend descent'''
        batch_num = 0
        for j in range(epochs):

            mini_batches_image = [train_image[k:k + mini_batch_size] for k in
                                  range(0, len(train_image), mini_batch_size)]
            mini_batches_label = [train_label[k:k + mini_batch_size] for k in
                                  range(0, len(train_label), mini_batch_size)]
            for mini_batch_image, mini_batch_label in zip(mini_batches_image, mini_batches_label):
                batch_num += 1
                if batch_num * mini_batch_size > len(train_image):
                    batch_num = 1

                self.update_mini_batch(mini_batch_image, mini_batch_label, eta, mini_batch_size)

                # if batch_num % 100 == 0:
                # print("after {0} training batch: accuracy is {1}/{2}".format(batch_num, self.evaluate(train_image[0:1000], train_label[0:1000]), len(train_image[0:1000])))

                print("\rEpoch{0}:{1}/{2}".format(j + 1, batch_num * mini_batch_size, len(train_image)), end=' ')

            print("After epoch{0}: accuracy is {1}/{2}".format(j + 1, self.evaluate(test_image, test_label),
                                                               len(test_image)))

    def update_mini_batch(self, mini_batch_image, mini_batch_label, eta, mini_batch_size):
        '''通过一个batch的数据对神经网络参数进行更新
        需要先求这个batch中每张图片的误差反向传播求得的权重梯度以及偏置梯度'''

        nabla_b = [np.zeros(b.shape) for b in self.biases]
        nabla_w = [np.zeros(w.shape) for w in self.weights]

        nabla_f = [np.zeros(f.shape) for f in self.filters]
        nabla_fb = [np.zeros(fb.shape) for fb in self.filters_biases]

        for x, y in zip(mini_batch_image, mini_batch_label):
            delta_nabla_w, delta_nabla_b, delta_nabla_f, delta_nabla_fb = self.backprop(x, y)
            nabla_b = [nb + dnb for nb, dnb in zip(nabla_b, delta_nabla_b)]
            nabla_w = [nw + dnw for nw, dnw in zip(nabla_w, delta_nabla_w)]
            nabla_f = [nf + dnf for nf, dnf in zip(nabla_f, delta_nabla_f)]
            nabla_fb = [nfb + dnfb for nfb, dnfb in zip(nabla_fb, delta_nabla_fb)]
        self.weights = [w - (eta / mini_batch_size) * nw for w, nw in zip(self.weights, nabla_w)]
        self.biases = [b - (eta / mini_batch_size) * nb for b, nb in zip(self.biases, nabla_b)]
        self.filters = [f - (eta / mini_batch_size) * nf for f, nf in zip(self.filters, nabla_f)]
        self.filters_biases = [fb - (eta / mini_batch_size) * nfb for fb, nfb in zip(self.filters_biases, nabla_fb)]

    def backprop(self, x, y):

        '''计算通过单幅图像求得梯度'''

        # 先前向传播，求出各中间量
        # 第一层卷积
        conv1 = add_bias(conv(x, self.filters[0]), self.filters_biases[0])
        relu1 = relu(conv1)
        pool1, pool1_max_locate = pool(relu1)

        # 第二层卷积
        conv2 = add_bias(conv(pool1, self.filters[1]), self.filters_biases[1])
        relu2 = relu(conv2)
        pool2, pool2_max_locate = pool(relu2)

        # 拉直
        straight_input = pool2.reshape(pool2.shape[0] * pool2.shape[1] * pool2.shape[2], 1)

        # 第一层全连接
        full_connect1_z = np.dot(self.weights[0], straight_input) + self.biases[0]
        full_connect1_a = relu(full_connect1_z)

        # 第二层全连接
        full_connect2_z = np.dot(self.weights[1], full_connect1_a) + self.biases[1]
        full_connect2_a = relu(full_connect2_z)

        # 第三层全连接（输出）
        full_connect3_z = np.dot(self.weights[2], full_connect2_a) + self.biases[2]
        full_connect3_a = soft_max(full_connect3_z)

        # 在这里我们使用交叉熵损失，激活函数为softmax，因此delta值就为 a-y，即对正确位置的预测值减1
        delta_fc3 = full_connect3_a - y
        delta_fc2 = np.dot(self.weights[2].transpose(), delta_fc3) * relu_prime(full_connect2_z)
        delta_fc1 = np.dot(self.weights[1].transpose(), delta_fc2) * relu_prime(full_connect1_z)
        delta_straight_input = np.dot(self.weights[0].transpose(), delta_fc1)  # 这里没有激活函数？
        delta_pool2 = delta_straight_input.reshape(pool2.shape)

        delta_conv2 = pool_delta_error_bp(delta_pool2, pool2_max_locate) * relu_prime(conv2)

        delta_pool1 = conv(padding(delta_conv2, self.filters[1].shape[1] - 1), rot180(self.filters[1]).swapaxes(0, 3))

        delta_conv1 = pool_delta_error_bp(delta_pool1, pool1_max_locate) * relu_prime(conv1)

        # 求各参数的导数
        nabla_w2 = np.dot(delta_fc3, full_connect2_a.transpose())
        nabla_b2 = delta_fc3
        nabla_w1 = np.dot(delta_fc2, full_connect1_a.transpose())
        nabla_b1 = delta_fc2
        nabla_w0 = np.dot(delta_fc1, straight_input.transpose())
        nabla_b0 = delta_fc1

        nabla_filters1 = conv_cal_w(delta_conv2, pool1)
        nabla_filters0 = conv_cal_w(delta_conv1, x)
        nabla_filters_biases1 = conv_cal_b(delta_conv2)
        nabla_filters_biases0 = conv_cal_b(delta_conv1)
        # print(x.shape, delta_conv1.shape, nabla_filters0.shape)

        nabla_w = [nabla_w0, nabla_w1, nabla_w2]
        nabla_b = [nabla_b0, nabla_b1, nabla_b2]
        nabla_f = [nabla_filters0, nabla_filters1]
        nabla_fb = [nabla_filters_biases0, nabla_filters_biases1]
        return nabla_w, nabla_b, nabla_f, nabla_fb


def main():
    # image维度为 num×rows×cols×1，像素值范围在0-1
    # label维度为num×class_num×1
    train_image, train_label, test_image, test_label = dataset_loader()

    num = 1000
    train_image = train_image[:num]
    train_label = train_label[:num]
    test_image = test_image[:num]
    test_label = test_label[:num]

    net = ConvNet()
    net.SGD(train_image, train_label, test_image, test_label, 5, 100, 3e-5)
    # net.SGD(train_image, train_label, test_image, test_label, 2, 200, 5)


if __name__ == '__main__':
    main()