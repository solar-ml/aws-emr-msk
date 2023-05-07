## Proposed solution description

Electrical faults in PV systems may evolve due to several abnormalities in internal configuration. We are presented with the task of **building an early detection and fault classification algorithm that uses the available electrical and environmental measurements from the sensors** deployed by most manufacturers of PV equipment.

On figure 1 a typical configuration of PV system presented consisting of 5 × 3 PV array and a boost converter programmed with an MPPT algorithm to operate the PV module at their maximum power point (MPP).
![](i/panel_schema.jpg)

in addition to a disconnection circuit and a servo motor mounted on it, normally each panel of the PV system is equipped with four sensors namely: **voltage**, **current**, **temperature** and **irradiance**. All these components are connected to microcontroller unit (MCU). 

The readings from the four sensors, together with the `deviceID` and `timestamp`, is regularly sent from the MCU to the remote terminal unit and then to the SCADA system. 

Further, the data from SCADA is streamed into Apache Kafka, either deployed locally or in the cloud. In our case, input information is available at Amazon Managed Streaming for Apache Kafka (Amazon MSK). The name of the input topic is `solar.data.segment.01`. Data schema shown below:

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
To estimate the size of the incoming data stream, we consider the size of each data point and the rate at which they are generated. Assuming readings from 4 sensors deployed on 10,000 solar panels are collected into the SCADA system every 20 seconds for 24 hours.

Device ID: string of 10 characters (alphanumeric ASCII characters, stored in UTF-8), each would take up 1 byte, then each device ID is 10 bytes.
Timestamp: A TimestampType() in PySpark corresponds to 8 bytes (64 bits).
Sensor readings: There are 4 sensor readings, each a 32-bit float, which totals to 4 * 4 bytes = 16 bytes. Therefore, each data point takes 10 + 8 + 16 = 34 bytes.

Number of data points per device in 24 hours = (24 hours * 60 minutes/hour * 60 seconds/minute) / 20 seconds = 4,320. Total number of data points from all devices in 24 hours = 10,000 devices * 4,320 data points/device = 43,200,000 data points. 

Total batch size = 43,200,000 data points * 34 bytes/data point = 1,468,800,000 bytes = 1.47GB

From Amazon MSK the data is ingested into Amazon EMR (Amazon Elastic MapReduce), a Spark/Hadoop/Hive cluster deployed on AWS. For this particular task, we chose a 24-hour batch window. So data is consumed from 0:00 to 23:59:59 the day before the current day. This window can be adjusted and predictive model can be applied more frequently to narrower ranges of data. However, this will incur additional charges from EMR.

Moreover, our pipeline can also be transformed into a near real-time streaming application. To do this, we can use Spark Structured Streaming features with a tumbling window over short time range (`timestamp`) and watermarking. We then apply CWT to the data bucketed within this window. The results are fed into a predictive model. Processed dataset where each device state within a given interval, classified into 6 fault types, is exposed via web service for use in the analytical dashboard and predictive maintenance reporting. This provides users with fast and granular PV array status updates. However, this use case requires the EMR cluster to run continuously, deployed on EC2 instances or EKS.

For modelling we combine methods #1 and #5 from the [electrical fault diagnosis methods](<Fault_Detection_and_Classification_in_Photovoltaic_Arrays.md>):

#### 1. **Statistical and Signal Processing** with Continuous Wavelet Transformation (CWT) 

In the first part, we will use [Continuous Wavelet Transformation](<Wavelet_Transform_intro.md>) to convert time series readings of voltage, current, temperature and irradiance into four coefficient matrices.

As opposed to Fast Fourier Transform (FFT) which only provides frequency information but loses time information, Wavelet Transform allows simultaneous analysis of **both time and frequency**. This is particularly useful for non-stationary signals, where the frequency content changes over time.

The result of applying CWT to time series data are 2D matrices called "scalograms". The "level of detail" is controlled by the "scale" parameter. The scale factor corresponds to how much a signal is scaled in time and is inversely proportional to frequency.

On figure 2 Visualization of ‘‘average scalograms’’ for six fault classes.
![](i/scalo_vis.jpg)

#### 2. **Convolutional Neural Network** (CNN) for multi-class fault classification

For the second part our approach is based on the use of a LeNet-style convolutional neural network (CNN) to predict whether a given panel is under certain fault conditions, such as Line-Line, Line-Ground, Open Circuit, Partial Shading, Arc Fault or none, by extracting features from two-dimensional (2-D) scalograms generated in real time by the PV data acquisition system.

An equally viable option is to use transfer learning by fine-tuning the last fully connected layer of the pre-trained AlexNet CNN and modifying its architecture to get only last 6 neurons which represent our 6 fault classes.

Third option is using Principal Components Analysis (PCA) to select the most important coefficients per scale to feed them to XGBoost classifier. 

We will use CNNs because they are very efficient at learning characteristic patterns of labels in images. This type of neural network can also treat the 2D CWT coefficients as pixels of an image to predict the corresponding activity.

To transform the signals of the solar PV dataset using the `pywt.cwt()` function, we choose the Morlet mother wavelet and a scale size of 64.

It is important to clarify how to feed the resulting CWT coefficient matrices into the CNN. The best approach here is to **layer the 2D coefficients** (images) of the four signals like the three Red, Green, Blue (RGB) channels of a colour image. This allows all the **dependencies between the different sensor data to be taken into account simultaneously**, which is very important.

The final step is to normalise and transform the data into the shape the neural network expects and apply the stored pre-trained model to classify and detect 6 types of faults.

With an accuracy of more than 90%, it can be concluded that the combination of CWT and CNN is a reasonable option for the classification of non-stationary multiple time series/signals.

By improving the CNN (adding regularisation, more neurons, etc.), different CNN architectures, hyperparameter tuning, or different scale sizes (with or without down-sampling), better results can be achieved.

### Code execution flow

Let us go through the step necessary to transform the data and apply the classification model:

1. First script `ingest_data.py` is submitted to Spark / EMR. It reads data from Kafka topic for 24 hours of the previous day into PySpark. For this, we use the `startingTimestamp' and `endingTimestamp' consumer parameters to filter the required timestamps. The Kafka server URI is obtained from the AWS System Manager Parameter Store.

2. Next, we apply the Continuous Wavelet Transform (CWT) using the Morlet mother wavelet with a scale of 64, and then stack the 2D scalograms like channels of a colour image, making them suitable for feeding into a CNN with LeNet-5 architecture for 64x64 images.

3. Next, we normalise and save the processed data in Parquet format to the S3 silver (staging) bucket.

4. Second script in pipeline `predict_fault.py` loads parquet file, feeds into pre-trained LeNet, gets its prediction classes, appends classes as extra column and stores result in gold S3 bucket. The names of the silver and gold S3 buckets are also obtained from the AWS System Manager Parameter Store. 