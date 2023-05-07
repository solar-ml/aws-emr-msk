## Fault Detection and Classification in Photovoltaic Arrays
#solar_pipeline

![](i/solar_plant_desert.jpg)

Renewable energy already accounts for a large part of the energy market. In recent decades, solar photovoltaic (PV) energy has rapidly captured a large number of markets due to its global availability, modularity, non-pollution, ease of installation, and affordability. Much progress has been made in the study of PV systems, especially in terms of efficiency, cost, and obtaining maximum available power from PV cells. Nevertheless, PV systems are often subject to a variety of types of faults, which can seriously affect the safe operation and conversion efficiency of the systems

The Energy Audit Report shows an annual energy loss of up to 18.9% due to PV system faults in the UK alone. Furthermore, the fault diagnosis of PV systems also yields numerous economic benefits. Therefore, it is necessary to focus attention on this task.

Faults in photovoltaic (PV) systems are mainly PV system component faults, which originate from dirty modules, sand or snow cover, local shading, module aging, and basic component manufacturing. The typical faults that occur in PV systems are shown in Figure 1, and can be divided into three types, namely, **physical**, **chemical**, and **electrical** faults.
![](i/fault_types_solar_panel.jpg)

To investigate and mitigate the aforementioned faults, National Electric Code (NEC) recommends the use of Ground Fault Protection Device, Over Current Protection Device and arc Fault Circuit Interrupter to detect Line-Line, Line-Ground and Arc faults respectively. However, the incompatibility of such protection devices is portrayed in comprehensive studies. 

Specifically, the nonlinear characteristics of PV arrays, low irradiance, maximum power point tracker, faults impedance, degradation and presence of blocking diodes are some factors that prevent protection devices to trip under certain conditions. Hence, sometime faults may go undetected for a long time, showing practical limitations of conventional protection schemes in PV arrays.

### Fault diagnosis methods

In general, there are two kinds kinds of fault diagnosis methods, i.e., **electrical methods**, and **thermal and visual methods**. 

The **visual and thermal methods** (infrared, thermal imagining, and thermal IR video) work well for PV panel hot-spot detection, yet require high initial investment in cameras or in fleet of unmanned aerial vehicles (UAV).

The **electrical methods** can be can be further classiﬁed into: 
1. **Statistical and signal processing** identifies faults by analyzing signals such as power data in a time in a series. This method has a high corrent diagnostic rate but requires many pre-processed data and a complex analysis process.
2. **Power loss analysis** achieves this by analyzing the output power loss on the DC side of PV systems, which reduces the computational and simulation costs, but does not distinguish the exact type of fault.
3. **Voltage and current measurement** detects the occurrence of faults by measuring the relevant voltage and current data, and comparing them with those in normal operation. This method is intuitive and simple, but the diagnostic accuracy is not high.
4. **I–V curve** can reveal the changes in a PV module. The module changes when different faults occur, and the faults can be identiﬁed by comparing the curve under the same external conditions. Fault analysis using I–V is intuitive and can help verify the health of a PV module during commissioning.
5. **Machine Learning and Artificial Neural Networks** techniques achieve automatic fault diagnosis by analysing a large amount of data. Compared with other methods, ML & ANN has a wider scope of application, not only for electrical parameters, but also for images and other information. It has advantages such as high diagnostic accuracy, low cost, accurate classification of fault types and better diagnostic performance for complex faults.

### Proposed solution description

Electrical faults in PV systems may evolve due to several abnormalities in internal configuration. We are presented with the task of **building an early detection and fault classification algorithm that uses the available electrical and environmental measurements from the sensors** deployed by most manufacturers of PV equipment.

On figure 2 a typical configuration of PV system presented consisting of 5 × 3 PV array and a boost converter programmed with an MPPT algorithm to operate the PV module at their maximum power point (MPP).
![](i/panel_schema.jpg)

in addition to a disconnection circuit and a servo motor mounted on it, normally each panel of the PV system is equipped with four sensors namely: **voltage**, **current**, **temperature** and **irradiance**. All these components are connected to microcontroller unit (MCU). 

The readings from the four sensors, together with the `deviceID` and `timestamp`, is regularly sent from the MCU to the remote terminal unit and then to the SCADA system. 

Futher, the data from SCADA is streamed into Apache Kafka, either deployed locally or in the cloud. In our case, input information is available at Amazon Managed Streaming for Apache Kafka (Amazon MSK). The name of the input topic is `solar.data.segment.01`. Schema presented below:

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

From Amazon MSK the data is ingested into Amazon EMR (Amazon Elastic MapReduce), a Spark cluster deployed on AWS. For this particular task, we chose a 24-hour batch window. So data is consumed from 0:00 to 23:59:59 the day before the current day. This window can be adjusted and predictive model can be applied more frequently to narrower ranges of data. However, this will incur additional charges from EMR.

For modelling we combine methods #1 and #5 from the electrical fault diagnosis methods above:

#### 1. **Statistical and Signal Processing** with Continuous Wavelet Transformation (CWT) 

As opposed to Fast Fourier Transform (FFT) which only provides frequency information bu÷t loses time information, Wavelet Transform allows simultaneous analysis of **both time and frequency**. This is particularly useful for non-stationary signals, where the frequency content changes over time.

The result of CWT application to a time-series data is 2D so called "scalograms". The "level of details" is controlled by `scale` parameter . The scale factor corresponds to how much a signal is scaled in time and it is inversely proportional to frequency. 

On figure 3 Visualization of ‘‘average scalograms’’ for six fault classes.
![](i/scalo_vis.jpg)

#### 2. **Convolutional Neural Network** (CNN) for multi-class fault classification

For the second part our approach is based on the use of a LeNet-style convolutional neural network (CNN) to predict whether a given panel is under certain fault conditions, such as Line-Line, Line-Ground, Open Circuit, Partial Shading, Arc Fault or none, by extracting features from two-dimensional (2-D) scalograms generated in real time by the PV data acquisition system.

An equally viable option is to use transfer learning by fine-tuning the last fully connected layer of the pre-trained AlexNet CNN and modifying its architecture to get only 6 neurons which represent our 6 fault classes.

Third option is using Principal Components Analysis (PCA) to select the most important coefficients per scale to feed them to XGBoost classifier. 

We will use CNNs because they are very efficient at learning characteristic patterns of labels in images. This type of neural network can also treat the 2D CWT coefficients as pixels of an image to predict the corresponding activity.

To transform the signals of the solar PV dataset using the `pywt.cwt()` function, we choose the Morlet mother wavelet and a scale size of 64.

It is important to clarify how to feed the resulting CWT coefficient matrices into the CNN. The best approach here is to **layer the 2D coefficients** (images) of the four signals like the three Red, Green, Blue (RGB) channels of a colour image. This allows all the **dependencies between the different sensor data to be taken into account simultaneously**, which is very important.

The final step is to normalise and transform the data into the shape the neural network expects and apply the stored pre-trained model to classify and detect 6 types of faults.

With an accuracy of more than 90%, it can be concluded that the combination of CWT and CNN is a reasonable option for the classification of non-stationary multiple time series/signals.

By improving the CNN (adding regularisation, more neurons, etc.), different CNN architectures, hyperparameter tuning, or different scale sizes (with or without down-sampling), better results can be achieved.

### Code execution flow

Let us go through the step necessary to transform the data and apply the classification model:

1. First script `data_ingest.py` is submitted to Spark / EMR. It reads data from Kafka topic for 24 hours of the previous day into PySpark. For this, we use the `startingTimestamp' and `endingTimestamp' consumer parameters to filter the required timestamps. The Kafka server URI is obtained from the AWS System Manager Parameter Store.

2. Next, we apply the Continuous Wavelet Transform (CWT) using the Morlet mother wavelet with a scale of 64, and then stack the 2D scalograms like channels of a colour image, making them suitable for feeding into a CNN with LeNet-5 architecture for 64x64 images.

3. Next, we normalise and save the processed data in Parquet format to the S3 silver (staging) bucket.

4. Second script in pipeline `predict_fault.py` loads parquet file, feeds into pre-trained LeNet, gets its prediction classes, appends classes as extra column and stores result in gold S3 bucket. The names of the silver and gold S3 buckets are also obtained from the AWS System Manager Parameter Store. 