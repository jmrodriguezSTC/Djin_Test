import clr #package pythonnet, not clr
import os


openhardwaremonitor_hwtypes = ['Mainboard','SuperIO','CPU','RAM','GpuNvidia','GpuAti','TBalancer','Heatmaster','HDD']

def initialize_openhardwaremonitor():
    dll_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "OpenHardwareMonitorLib.dll")
    clr.AddReference(dll_path)

    from OpenHardwareMonitor import Hardware

    handle = Hardware.Computer()
    handle.MainboardEnabled = True
    handle.CPUEnabled = True
    handle.RAMEnabled = True
    handle.GPUEnabled = True
    handle.HDDEnabled = True
    handle.Open()
    return handle


def fetch_stats(handle):
    for i in handle.Hardware:
        i.Update()
        for sensor in i.Sensors:
            parse_sensor(sensor)
        for j in i.SubHardware:
            j.Update()
            for subsensor in j.Sensors:
                parse_sensor(subsensor)


def parse_sensor(sensor):
        if sensor.Value is not None:
            if type(sensor).__module__ == 'OpenHardwareMonitor.Hardware':
                hardwaretypes = openhardwaremonitor_hwtypes
            else:
                return

            if sensor.SensorType.ToString() == 'Temperature':
                print(u"%s %s %s Sensor #%i %s - %s" % (hardwaretypes[sensor.Hardware.HardwareType], sensor.Hardware.Name, sensor.SensorType.ToString(), sensor.Index, sensor.Name, sensor.Value))
            # \u00B0C
            
if __name__ == "__main__":
    print("OpenHardwareMonitor:")
    HardwareHandle = initialize_openhardwaremonitor()
    fetch_stats(HardwareHandle)