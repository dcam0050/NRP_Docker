@nrp.MapRobotSubscriber("joint_state", Topic('/joint_states', sensor_msgs.msg.JointState))
@nrp.MapCSVRecorder("recorder", filename="all_joints_positions.csv", headers=["Name", "time", "Position"])
@nrp.Robot2Neuron()
def csv_joint_state_monitor(t, joint_state, recorder):
    if not isinstance(joint_state.value, type(None)):
        for i in range(0, len(joint_state.value.name)):
            recorder.record_entry(joint_state.value.name[i], t, joint_state.value.position[i])
