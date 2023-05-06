## Fault Detection and Classification in Photovoltaic Arrays

![](i/1d7fb93a-7589-4e01-b009-39803cb11ca4.jpg)

Renewable energy already accounts for a large part of the energy market. In recent decades, solar photovoltaic (PV) energy has rapidly captured a large number of markets due to its global availability, modularity, non-pollution, ease of installation, and affordability. Much progress has been made in the study of PV systems, especially in terms of efficiency, cost, and obtaining maximum available power from PV cells. Nevertheless, PV systems are often subject to a variety of types of faults, which can seriously affect the safe operation and conversion efficiency of the systems

The Energy Audit Report shows an annual energy loss of up to 18.9% due to PV system faults in the UK alone. Furthermore, the fault diagnosis of PV systems also yields numerous economic benefits. Therefore, it is necessary to focus attention on this task.

Faults in photovoltaic (PV) systems are mainly PV system component faults, which originate from dirty modules, sand or snow cover, local shading, module aging, and basic component manufacturing. The typical faults that occur in PV systems are shown in Figure 1, and can be divided into three types, namely, **physical**, **chemical**, and **electrical** faults.

![](i/352f01f3-1499-4ea3-a5fe-3638de343841.jpg)


To investigate and mitigate the aforementioned faults, article 690 in National Electric Code (NEC) recommends the use of Ground Fault Protection Device (GFPD), Over Current Protection Device (OCPD) and arc Fault Circuit Interrupter (AFCI) to detect Line-Line, Line-Ground and Arc faults respectively. However, the incompatibility of such protection devices is portrayed in comprehensive studies. 

Specifically, the nonlinear characteristics of PV arrays, low irradiance, maximum power point tracker (MPPT), faults impedance, degradation and presence of blocking diodes are some factors that prevent protection devices to trip under certain conditions. Hence, sometime faults may go undetected for a long time, showing practical limitations of conventional protection schemes in PV arrays.

### Fault diagnosis methods

In general, there are two kinds kinds of fault diagnosis methods, i.e., **electrical methods**, and **thermal and visual methods**. 

The **visual and thermal methods** (infrared, thermal imagining, and thermal IR video) work well for PV panel hot-spot detection, yet require high initial investment in cameras or in fleet of unmanned aerial vehicles (UAV).

The **electrical methods** can be can be further classiﬁed into: 
1. **Statistical and signal processing** identifies faults by analyzing signals such as power data in a time in a series. This method has a high corrent diagnostic rate but requires many pre-processed data and a complex analysis process.
2. **Power loss analysis** achieves this by analyzing the output power loss on the DC side of PV systems, which reduces the computational and simulation costs, but does not distinguish the exact type of fault.
3. **Voltage and current measurement** detects the occurrence of faults by measuring the relevant voltage and current data, and comparing them with those in normal operation. This method is intuitive and simple, but the diagnostic accuracy is not high.
4. **I–V curve** can reveal the changes in a PV module. The module changes when different faults occur, and the faults can be identiﬁed by comparing the curve under the same external conditions. Fault analysis using I–V is intuitive and can help verify the health of a PV module during commissioning.
5. **Machine Learning and Artificial Neural Network** techniques achieve automatic fault diagnosis by analysing a large amount of data. Compared with other methods, ML & ANN has a wider scope of application, not only for electrical parameters, but also for images and other information. It has advantages such as high diagnostic accuracy, low cost, accurate classification of fault types and better diagnostic performance for complex faults.

### Business case description

PV systems are frequently challenged by the occurrence of a number of electrical faults that may evolve due to several abnormalities in internal configuration. We are presented with the task of building an early detection and fault classification algorithm that uses the available electrical and environmental measurements from the sensors deployed by most manufacturers of PV equipment.
![](i/Panel_schema.jpg)

It should be noted that, in addition to a disconnection circuit and a servo motor mounted on it, normally each panel of the PV system is equipped with four sensors namely: **voltage**, **current**, **temperature** and **irradiance** sensor. All these components are connected to microcontroller unit (MCU). 

The information from the four sensors, together with the device ID and time stamp, is regularly sent from the MCU to the remote terminal unit and then to the SCADA system. 

Next, the data is streamed to Apache Kafka, either deployed locally or in the cloud. In our case, input information is available at Amazon Managed Streaming for Apache Kafka (Amazon MSK). The name of the input topic is `solar.data.segment.01`. Schema presented below:

```python
schema = StructType([
        StructField("deviceID", StringType(), True),
        StructField("timestamp", TimestampType(), True),
        StructField("voltage", FloatType(), True),
        StructField("current", FloatType(), True),
        StructField("temperature", FloatType(), True),
        StructField("irradiance", FloatType(), True)
    ])
```

Data ingested into Amazon EMR (Amazon Elastic MapReduce), a Spark cluster deployed on AWS. For this particular task, we chose a 24-hour batch window. So data is consumed from 0:00 to 23:59:59 the day before the current day. Of course, this window can be made smaller to increase classification performance by applying the predictive model more frequently to narrower ranges of data. However, this will incur additional charges from EMR.

For modelling we combine methods #1 and #5 from the list above:
- **Statistical and Signal Processing** with Continuous Wavelet Transformation (CWT) 
- **Convolutional Neural Network** (CNN) for multi-class fault classification

Our approach is based on the use of a pre-trained LeNet-style convolutional neural network (CNN) to predict whether a given panel is under certain fault conditions, such as Line-Line, Line-Ground, Open Circuit, Partial Shading, Arc Fault or none, by extracting features from two-dimensional (2-D) scalograms generated in real time by the PV data acquisition system.

CNN typically are highly efficient at learning characteristic patterns of labels in images. This type of neural network can also treat the 2D CWT coefficients as pixels of an image to predict the corresponding activity. 

To transform signals of the solar PV data set using the `pywt.cwt()` function we choose the Morlet mother wavelet and a scale size of 64. 

Importantly, we must clarify how to feed the resulting CWT coefficient matrices into the CNN.  Here, the best approach is to place the 2D coefficients (images) of the four signals on each other like the three channels red, green, blue (RGB) of a color image. Accordingly, all dependencies between the different sensor data can be taken into account simultaneously, which is very important.

1. First script `data_ingest.py` will be submitted to Spark / EMR. It reads data from Kafka topic for the last 24 hours into PySpark. For that we use `startingTimestamp` and `endingTimestamp` consumer params to filter required timestamps.  Kafka server URI obtained form AWS System Manager Parameter Store.

2. Next we apply the Continuous Wavelet Transform (CWT) using the Morlet mother wavelet with a scale size of 64, and then stacks the 2D scalograms like channels of a color image, making it suitable for feeding into a CNN with LeNet-5 architecture for 64x64 images.

3. Next we normalize and save processed data in Parquet format to S3 silver (staging) bucket.

4. Second script of the pipeline `predict_fault.py` loads Parquet file, feeds into pre-trained LeNet, gets its prediction classes, appends classes as extra column and saves the result into gold S3 bucket. S3 silver and gold buckets names also obtained from AWS System Manager Parameter Store.


#### Real-time monitoring of partial shading in large PV plants using Convolutional Neural Network
https://www.sciencedirect.com/science/article/abs/pii/S0038092X23001263?via%3Dihub

The performance of a typical string-connected Photovoltaic (PV) panels will be adversely affected even if only one of its panels is partially shaded. Therefore, the monitoring of these panels becomes crucial to ensure reliable operation of the whole PV plant. In this paper, a low-cost solution for real-time monitoring and diagnosis of PV plants is proposed. In fact, our approach is based on the use of pre-trained AlexNet Convolutional Neural Network (CNN) to predict whether a given panel is under partial shading conditions (PSC) or not, by extracting features from two-dimensional (2-D) scalograms generated in real-time from PV data acquisition system. 

It should be noted that, in addition to a disconnection circuit and a servo motor mounted on it, each panel of the proposed system is equipped with four sensors namely: voltage, current, temperature and irradiance sensor. All these components are connected to Adafruit PyBadge microcontroller unit (MCU). In fact, a Continuous Wavelet Transform was applied to the time series data provided by these sensors to generate the 2-D scalograms. 

On the hand, we performed transfer learning by fine-tuning the last fully connected layer of the pre-trained AlexNet CNN and modifying its architecture to get only two neurons which represent our two classes (i.e., PV panel under PSC or not). The model, achieving a high fault detection accuracy of 98.05%, was built in Keras framework with TensorFlow where only the parameters of the last fully connected layer of the pre-trained AlexNet CNN are retrained. Afterward, this model was converted into TensorFlow Lite format and successfully implemented on PyBadge MCU. 

Several experiments were carried out in this work have shown that, our monitoring system allows not only the automatic disconnection of the partial shaded PV panels, to avoid thermal issues under bypass conditions, but also removing undesired objects accumulated on their surface by actioning the corresponding servo motor, in order to restore in real-time the normal operation of the whole PV system.


