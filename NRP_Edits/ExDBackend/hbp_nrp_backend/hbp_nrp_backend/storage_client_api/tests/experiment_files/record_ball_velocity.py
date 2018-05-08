# Imported Python Transfer Function
import numpy as np
import sensor_msgs.msg
# @nrp.MapCSVRecorder("ball_recorder", filename="ball_states.csv",
#                     headers=["Time", "Position", "Velocity"])

@nrp.MapCSVRecorder("ball_recorder", filename="ball_states.csv",
                    headers=["Time", "px", "py", "pz"])
@nrp.Robot2Neuron()
def record_ball_csv(t, ball_recorder):
    from rospy import ServiceProxy
    from gazebo_msgs.srv import GetModelState

    model_name = 'ball'
    state_proxy = ServiceProxy('/gazebo/get_model_state',
                                    GetModelState, persistent=False)
    ball_state = state_proxy(model_name, "world")

    if ball_state.success:
        current_position = ball_state.pose.position
        ball_recorder.record_entry(t,
                                   current_position.x,
                                   current_position.y,
                                   current_position.z)

