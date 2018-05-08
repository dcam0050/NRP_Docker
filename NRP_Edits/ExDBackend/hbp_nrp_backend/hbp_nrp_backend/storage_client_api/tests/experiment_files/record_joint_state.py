# Imported Python Transfer Function
import numpy as np
import sensor_msgs.msg

@nrp.MapRobotSubscriber("joint_states", Topic('/robot/joints',
                                              sensor_msgs.msg.JointState))
@nrp.MapCSVRecorder("joint_recorder", filename="joint_states.csv",
                    headers=["Time", "Name", "Position"])
@nrp.Robot2Neuron()
def record_joint_csv(t, joint_states, joint_recorder):
    if not isinstance(joint_states.value, type(None)):
        for i in range(0, len(joint_states.value.name)):
            joint_recorder.record_entry(t,
                                        joint_states.value.name[i],
                                        joint_states.value.position[i]
                                        )


