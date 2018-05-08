{% if __builtins__.type(tf) == bibi_api_gen.PythonTransferFunction %}
{% for cont in tf.orderedContent() %}
{{correct_indentation(cont.value, 1)}}
{% endfor %}

{% elif __builtins__.type(tf) == bibi_api_gen.Neuron2Robot %}

{% for dyn in dynamics %}
    {{dyn.name}} = {{print_synapse_dynamics(dyn)}}
{% endfor %}
{% for conn in connectors %}
    {{conn.name}} = {{print_connector(conn)}}
{% endfor %}
{% for topic in tf.topic %}
{% if is_not_none(topic.body) %}
    @nrp.MapRobotPublisher("{{topic.name}}", Topic('{{topic.topic}}', {{topic.type}}))
{% else %}
    @nrp.MapRobotSubscriber("{{topic.name}}", Topic('{{topic.topic}}', {{topic.type}}))
{% endif %}{% endfor %}
{% for dev in tf.device %}
{% if is_not_none(dev.body) %}
    @nrp.MapSpikeSource("{{dev.name}}", {{print_neurons(dev.neurons, "nrp.brain.")}}, nrp.{{get_device_name(dev.type)}}{{print_device_config(dev)}})
{% else %}
    @nrp.MapSpikeSink("{{dev.name}}", {{print_neurons(dev.neurons, "nrp.brain.")}}, nrp.{{get_device_name(dev.type)}}{{print_device_config(dev)}})
{% endif %}{% endfor %}
{% for group in tf.deviceGroup %}
{% if is_not_none(group.body) %}
    @nrp.MapSpikeSource("{{group.name}}", {{print_neuron_group(group.neurons)}}, nrp.{{get_device_name(group.type)}}{{print_device_config(group)}})
{% else %}
    @nrp.MapSpikeSink("{{group.name}}", {{print_neuron_group(group.neurons)}}, nrp.{{get_device_name(group.type)}}{{print_device_config(group)}})
{% endif %}{% endfor %}
    @nrp.Neuron2Robot({% if is_not_none(tf.returnValue) %}Topic('{{tf.returnValue.topic}}', {{tf.returnValue.type}}){% endif %})
    def {{tf.name}}(t{% for t in tf.topic %}, {{t.name}}{%endfor%}{% for dev in tf.device %}, {{dev.name}}{%endfor%}{% for group in tf.deviceGroup %}, {{group.name}}{%endfor%}):
{% for local in tf.local %}
        {{local.name}} = {{print_expression(local.body)}}
{% endfor %}
{% for dev in tf.device %}{% if is_not_none(dev.body) %}
        {{dev.name}}.{{get_default_property(dev.type)}} = {{print_expression(dev.body)}}
{% endif %}{% endfor %}
{% for group in tf.deviceGroup %}{% if is_not_none(group.body) %}
        {{group.name}}.{{get_default_property(group.type)}} = {{print_expression(group.body)}}
{% endif %}{% endfor %}
{% for top in tf.topic %}{% if is_not_none(top.body) %}
        {{top.name}}.send_message({{print_expression(top.body)}})
{% endif %}{% endfor %}
{% if is_not_none(tf.returnValue) %}
        return {{print_expression(tf.returnValue.body)}}
{% endif %}

{% elif __builtins__.type(tf) == bibi_api_gen.Neuron2Monitor %}

    @nrp.NeuronMonitor({{print_neurons(tf.device[0].neurons, "nrp.brain.")}}, nrp.{{get_device_name(tf.device[0].type)}})
    def {{tf.name}}(t):
        return True

{% elif __builtins__.type(tf) == bibi_api_gen.Robot2Neuron %}

{% for dyn in dynamics %}
    {{dyn.name}} = {{print_synapse_dynamics(dyn)}}
{% endfor %}
{% for conn in connectors %}
    {{conn.name}} = {{print_connector(conn)}}
{% endfor %}
{% for topic in tf.topic %}
{% if is_not_none(topic.body) %}
    @nrp.MapRobotPublisher("{{topic.name}}", Topic('{{topic.topic}}', {{topic.type}}))
{% else %}
    @nrp.MapRobotSubscriber("{{topic.name}}", Topic('{{topic.topic}}', {{topic.type}}))
{% endif %}{% endfor %}
{% for dev in tf.device %}
{% if is_not_none(dev.body) %}
    @nrp.MapSpikeSource("{{dev.name}}", {{print_neurons(dev.neurons, "nrp.brain.")}}, nrp.{{get_device_name(dev.type)}}{{print_device_config(dev)}})
{% else %}
    @nrp.MapSpikeSink("{{dev.name}}", {{print_neurons(dev.neurons, "nrp.brain.")}}, nrp.{{get_device_name(dev.type)}}{{print_device_config(dev)}})
{% endif %}{% endfor %}
{% for group in tf.deviceGroup %}{% if is_not_none(group.body) %}
    @nrp.MapSpikeSource("{{group.name}}", {{print_neuron_group(group.neurons)}}, nrp.{{get_device_name(group.type)}}{{print_device_config(group)}})
{% else %}
    @nrp.MapSpikeSink("{{group.name}}", {{print_neuron_group(group.neurons)}}, nrp.{{get_device_name(group.type)}}{{print_device_config(group)}})
{% endif %}{% endfor %}
    @nrp.Robot2Neuron()
    def {{tf.name}}(t{% for topic in tf.topic %}, {{topic.name}}{%endfor%}{% for dev in tf.device %}, {{dev.name}}{%endfor%}{% for group in tf.deviceGroup %}, {{group.name}}{%endfor%}):
{% for local in tf.local %}
        {{local.name}} = {{print_expression(local.body)}}
{% endfor %}
{% for dev in tf.device %}{% if is_not_none(dev.body) %}
        {{dev.name}}.{{get_default_property(dev.type)}} = {{print_expression(dev.body)}}
{% endif %}{% endfor %}
{% for group in tf.deviceGroup %}{% if is_not_none(group.body) %}
        {{group.name}}.{{get_default_property(group.type)}} = {{print_expression(group.body)}}
{% endif %}{% endfor %}
{% for top in tf.topic %}{% if is_not_none(top.body) %}
        {{top.name}}.send_message({{print_expression(top.body)}})
{% endif %}{% endfor %}
{% endif %}
