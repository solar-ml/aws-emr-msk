# Fault Detection and Classification in Photovoltaic Arrays

Draft notes on building an early detection and fault classification algorithm that uses the available electrical and environmental measurements from the sensors deployed by most major manufacturers of PV equipment.

In the first part, we will use Continuous Wavelet Transformation to convert time series readings from voltage, current, temperature and irradiance sensors into four coefficient matrices applied on a per-device basis.

For the second part our approach is based on the use of a LeNet-style convolutional neural network (CNN) to predict whether a given panel is under certain fault conditions, such as Line-Line, Line-Ground, Open Circuit, Partial Shading, Arc Fault or none, by extracting features from two-dimensional (2-D) scalograms generated in real time by the PV data acquisition system.

1. [Fault Detection and Classification in Photovoltaic Arrays](<Fault_Detection_and_Classification_in_Photovoltaic_Arrays.md>)

2. [Proposed solution](<Proposed_solution.md>)

3. [Wavelet Transformation Introduction](<Wavelet_Transform_intro.md>)

4. Python annotated source code. Also available at `./src` folder
- [Kafka to Spark data ingestion and CWT tranformation](<ingest_data_py.md>)
- [Applications of CNN fault classification model](<predict_fault_py.md>)
- [LeNet CNN reference architecture](<lenet_cnn_py.md>)
    