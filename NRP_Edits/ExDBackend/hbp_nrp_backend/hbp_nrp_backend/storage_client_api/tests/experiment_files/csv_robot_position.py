@nrp.MapCSVRecorder("recorder", filename="robot_position.csv", headers=["x", "y", "z"])
@nrp.MapRobotSubscriber("position", Topic('/gazebo/model_states', gazebo_msgs.msg.ModelStates))
@nrp.MapVariable("robot_index", global_key="robot_index", initial_value=None)
@nrp.Robot2Neuron()
def csv_robot_position(t, position, recorder, robot_index):
    if t == 0:
        robot_index.value = None
    if not isinstance(position.value, type(None)):
        if robot_index.value is None:
            robot_index.value = position.value.name.index('robot')
        recorder.record_entry(position.value.pose[robot_index.value].position.x,
                              position.value.pose[robot_index.value].position.y,
                              position.value.pose[robot_index.value].position.z)
