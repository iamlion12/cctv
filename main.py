import imageio
import mask_rcnn
import numpy as np
from keras.models import load_model
from keras.preprocessing import image

if __name__ == "__main__":

    """
    https://github.com/matterport/Mask_RCNN - репозиторий с Mask_RCNN, там есть все зависимости
    https://github.com/cocodataset/cocoapi - нужно обязательно установить для mask_rcnn
    Модель сама загрузится при первом запуске
    Вторая модель лежит тут https://yadi.sk/d/zmXBCvn93VkqGc
    """

    #цепляем mask_rcnn для того, чтобы выделять людей
    rcnn_model = mask_rcnn.load_mask_rcnn()

    #выделяем людей
    peoples = mask_rcnn.select_people(rcnn_model, image.img_to_array(image.load_img("./test.jpg")))

    #модель чтобы определять хороший человек или нет, [1, 0]-хороший [0, 1] - нет.
    model = load_model("./model.h5")

    #модель с кераса имеет статичный вход 128x128
    #чтобы получить нормальный выхлоп, можно к выходу нейронки применить np.argmax,
    #получится 0, если человек не нарушает, 1 если нарушает
    results = list([model.predict(np.array([image.img_to_array(image.array_to_img(people).resize((128,128)))])) for people in peoples])

    print(results)
