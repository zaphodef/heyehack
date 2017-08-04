// TODO: assert the RTT to the DNS is not too high

var HH = {};
HH.run = 0;
HH.after_N = 1;
HH.counter = 0;
HH.main_url = "ds.6cn-prs.6cn.io";
HH.base_host = "test." + HH.main_url;
HH.timeout = 7000;
HH.maxDelay = 6000;

HH.getms = function () {
    // Helper function to get the current date/time as milliseconds.
    var d = new Date();
    return d.getTime();
};

HH.reset_table = function() {
    // Reset stats relating to success/fail
    HH.tries = {};
    HH.tries.ipv4 = 0;
    HH.tries.ipv6 = 0;
    HH.tries.error = 0;
    HH.tries.timeout = 0;

    // Reset stats relating to timing
    HH.times = {};
    HH.times.ipv4 = [];
    HH.times.ipv6 = [];
    HH.times.error = [];
    HH.times.timeout = [];

    // Immediately show the stats to effectively clear the page
    HH.display_stats();
}

HH.reset_graph = function() {
    var ctx = document.getElementById("graph_stats");

    var labels = [];
    for (var i = -HH.maxDelay; i <= HH.maxDelay; i++) {
        labels.push(i);
    }

    var line_fifty = new Array(2*HH.maxDelay).fill(null);
    line_fifty[0] = 50;
    line_fifty[line_fifty.length - 1] = 50;

    HH.graph_stats = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [
            {
                // line at 50%
                data: line_fifty,
                spanGaps: true,
                yAxisID: 'percentage',
                xAxisID: 'xAxe',
                lineTension: 0,
                fill: false,
                borderColor: "rgba(200, 50, 50, 0.8)",
                borderCapStyle: "round",
                borderDash: [10,15],
            }, {
                data: new Array(2*HH.maxDelay).fill(null),
                spanGaps: true,
                yAxisID: 'percentage',
                xAxisID: 'xAxe',
                lineTension: 0,
                backgroundColor: 'rgba(40, 40, 40, 0.6)'
            }
            ],
            labels: labels,
        },
        options: {
            legend: {
                display: false,
            },
            scales: {
                xAxes : [{
                    id: 'xAxe',
                    ticks: {
                        min: 0,
                        max: 10,
                    },
                    position: 'bottom',
                    scaleLabel: {
                        display: true,
                        labelString: 'delay (ms)',
                    },
                }],
                yAxes: [{
                    id: 'percentage',
                    type: 'linear',
                    position: 'left',
                    scaleLabel: {
                        display: true,
                        labelString: 'IPv6 percentage',
                    },
                    ticks: {
                        min: 0,
                        max: 100,
                    }
                }]
            }
        }
    });
}

HH.reset = function() {
    // Reset counter, affects when we change random names next
    HH.counter = 0;

    HH.reset_table();

    // Clear the visual log
    $("#query_log").html("");

    HH.reset_graph();
    
    // Reset all alerts.
    HH.dismiss_alert();
};

HH.addDataToGraph = function(abs, ord) {
    HH.graph_stats.data.datasets[1].data[abs+HH.maxDelay] = ord;
    if (HH.graph_stats.options.scales.xAxes[0].ticks.max < abs) {
        HH.graph_stats.options.scales.xAxes[0].ticks.max = abs;
    }
    else if (HH.graph_stats.options.scales.xAxes[0].ticks.min > abs) {
        HH.graph_stats.options.scales.xAxes[0].ticks.min = abs;
    }
    HH.graph_stats.update();
};

HH.hide_graph = function() {
    // var $graph = $("#graph");
    // if ($graph.css("display") != 'none') $graph.toggle();
}

HH.show_graph = function() {
    // var $graph = $("#graph");
    // if ($graph.css("display") == 'none') $graph.toggle();
}

HH.alert = function(message, level) {
    var panel = document.createElement('div');
    panel.innerHTML = message;
    panel.className = ("alert alert-"+level);
    document.getElementById("hh_alert").appendChild(panel);
}

HH.dismiss_alert = function() {
    var mother_panel = document.getElementById("hh_alert");
    while (mother_panel.firstChild) {
        mother_panel.removeChild(mother_panel.firstChild);
    }
}

HH.inactivate_selections = function() {
    $("#n_1").attr("class","inactive");
    $("#n_10").attr("class","inactive");
    $("#n_100000").attr("class","inactive");
}

HH.random_after_N = function(i) {
    HH.after_N = i;
    HH.inactivate_selections();
    $("#n_" + i).attr("class","active");
};

HH.reset_delays = function() {
    document.getElementById('a_delay').value = 0;
    document.getElementById('aaaa_delay').value = 0;
    document.getElementById('synack_delay').value = 0;
}

HH.engage_buttons = function() {
    document.getElementById("button_start_stop").innerHTML = "Start";
    document.getElementById("button_start_stop").className = "btn btn-success";
    document.getElementById("sweep_aaaa").disabled = false;
    document.getElementById("sweep_synack").disabled = false;
}

HH.disengage_buttons = function() {
    document.getElementById("button_start_stop").innerHTML = "Stop";
    document.getElementById("button_start_stop").className = "btn btn-danger";
    document.getElementById("sweep_aaaa").disabled = true;
    document.getElementById("sweep_synack").disabled = true;
}

HH.engage_params = function() {
    var param_names = ["requests_number", "requests_delay", "aaaa_delay", "a_delay", "synack_delay"];
    for (var i=0, l = param_names.length; i<l; i++) {
        document.getElementById(param_names[i]).disabled = false;
    }
}

HH.disengage_params = function() {
    var param_names = ["requests_number", "requests_delay", "aaaa_delay", "a_delay", "synack_delay"];
    var l = param_names.length;
    for (var i=0, l = param_names.length; i<l; i++) {
        document.getElementById(param_names[i]).disabled = true;
    }
}

HH.stop = function() {
    if (HH.run == 1) {
        HH.run = 0;
        clearInterval(HH.interval);
        HH.engage_buttons();
        HH.engage_params();
        HH.dismiss_alert();
    }
};

HH.start = function() {
    if (HH.run == 0) {
        HH.dismiss_alert();
        HH.disengage_buttons();
        HH.hide_graph();
        var tmp = HH.get_frequency();
        var number = tmp[0], interval = tmp[1];
        HH.interval = setInterval(function() {HH.do_N_tests(number);}, interval);
        HH.run = 1;
    }
};

HH.display_stats_helper = function(x) {
    // see https://stackoverflow.com/questions/12862624/
    // and https://j11y.io/cool-stuff/double-bitwise-not/ for double bitwise NOT
    // (quick conversion to integer)
    var a, j, result;
    a = HH.times[x];
    j = jStat(a);

    result=jStat.median(a);
    result = (~~result) / 1000;
    if (!isNaN(result)) result = result + "s";
    $("td#median_" + x).text(result);

    result=jStat.stdev(a);
    result = (~~result) / 1000;
    if (!isNaN(result)) result = result + "s";
    $("td#stddev_" + x).text(result);

    result=jStat.sum(a);
    if (a.length > 0) result = result / a.length;
    else result = 0;
    result = (~~result) / 1000;
    if (!isNaN(result)) result = result + "s";
    $("td#average_" + x).text(result);
}

HH.display_stats = function() {
    $("td#ipv4").text(HH.tries.ipv4.toString());
    $("td#ipv6").text(HH.tries.ipv6.toString());
    $("td#error").text(HH.tries.error.toString());
    $("td#timeout").text(HH.tries.timeout.toString());

    var total =  HH.tries.ipv4 +  HH.tries.ipv6 +  HH.tries.error + HH.tries.timeout;
    if (total < 1) total = 1;

    $("td#percent_ipv4").text(~~(HH.tries.ipv4*10000 / total)/100 + '%');
    $("td#percent_ipv6").text(~~(HH.tries.ipv6*10000 / total)/100 + '%');
    $("td#percent_error").text(~~(HH.tries.error*10000 / total)/100 + '%');
    $("td#percent_timeout").text(~~(HH.tries.timeout*10000 / total)/100 + '%');

    HH.display_stats_helper("ipv4");
    HH.display_stats_helper("ipv6");
    HH.display_stats_helper("error");
    HH.display_stats_helper("timeout");
};

HH.gen_random = function(length, chars) {
    // http://stackoverflow.com/questions/10726909/random-alpha-numeric-string-in-javascript
	var mask = '';
    if (chars.indexOf('a') > -1) mask += 'abcdefghijklmnopqrstuvwxyz';
    if (chars.indexOf('A') > -1) mask += 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    if (chars.indexOf('#') > -1) mask += '0123456789';
    if (chars.indexOf('!') > -1) mask += '~`!@#$%^&*()_+-={}[]:";\'<>?,./|\\';
    var result = '';
    for (var i = length; i > 0; --i) result += mask[Math.floor(Math.random() * mask.length)];
    return result; 
}

HH.read_synack_delays = function() {
    var synack_v4_delay, synack_v6_delay, delay, delta_port, port;

    delay = document.getElementById('synack_delay').value;
    HH.assert_param('synack_delay', delay, -2999, 2999);

    var delay_ipv6 = delay<0;
    delay = ~~Math.abs(delay);

    /*
     * we have 500 ports for each protocol
     * 
     * the 300 first are used for delays between 0 and 600
     * with a granularity of 2
     * 
     * then the 100 next are used for delays between 601 and 1000
     * with a granularity of 4
     *
     * eventually the last 100 are used for delays between 1001 and 2999
     * with a granularity of 20
     */
    if (delay <= 600) delta_port = ~~(delay/2);
    else if (delay <= 1000) delta_port = 300 + ~~((delay-600)/4);
    else if (delay < 3000) delta_port = 400 + ~~((delay-1000)/20);
    else delta_port = 500; // the max we allow

    if (delay_ipv6) {
        // delay IPv6
        synack_v6_delay = delay;
        synack_v4_delay = 0
        port = 10500+delta_port;
    } else {
        // delay IPv4
        synack_v4_delay = delay;
        synack_v6_delay = 0;
        port = 10000+delta_port;
    }

    return [synack_v4_delay, synack_v6_delay, port];
}

HH.assert_param = function(id, value, min, max) {
    var warn = false;
    var new_val = value;
    if (value < min) {
        document.getElementById(id).value = min;
        new_val = min;
        warn = true;
    } else if (value > max) {
        document.getElementById(id).value = max;
        new_val = max;
        warn = true;
    }
    if (warn) HH.alert("<strong>WARNING:</strong> variable " + id + " outside the accepted range, automatically set it to the closest value allowed.", 'warning');
    return new_val;
}

HH.get_frequency = function() {
    var number = ~~document.getElementById("requests_number").value;
    var interval = ~~document.getElementById("requests_delay").value;
    number = HH.assert_param("requests_number", number, 1, 5);
    interval = HH.assert_param("requests_delay", interval, 100, Infinity);
    if (interval/number < 100) HH.alert("<strong>INFO:</strong> Keep in mind initiating tests too close to one another in time may flood your webbrowser and cause in approximative results. Note that the server may also slow you down.", 'info');
    return [number, interval];
}

HH.get_params = function() { 
    var r1, r2, a_delay, aaaa_delay, synack_v4_delay, synack_v6_delay, port,
        seed, test_url;
    if ((HH.counter % HH.after_N) == 0)  {
        r1 = HH.gen_random(14, "#a");
        r2 = r1;
        HH.last_random = r1;
    } else {
        r1 = HH.last_random;
        r2 = HH.gen_random(14, "#a");
    }
    HH.counter = HH.counter + 1;

    a_delay = ~~document.getElementById('a_delay').value;
    aaaa_delay = ~~document.getElementById('aaaa_delay').value;

    var synack_v4_delay, synack_v6_delay;
    var params = HH.read_synack_delays();
    synack_v4_delay = params[0];
    synack_v6_delay = params[1];
    port = params[2];

    HH.assert_param('a_delay', a_delay, 0, 5000);
    HH.assert_param('aaaa_delay', aaaa_delay, 0, 5000);

    seed = r1 + "-" + aaaa_delay + "-" + a_delay;
    test_url = "http://" + seed + "." + HH.base_host + ":" + port + "/ip";

    return [seed, a_delay, aaaa_delay, synack_v4_delay, synack_v6_delay, port, test_url];
};

HH.log_test = function(params, status, ts, delta_t) {
    var seed = params[0]; // debug purpose
    var a_delay_th = params[1];
    var aaaa_delay_th = params[2];
    var synack_v4_delay_th = params[3];
    var synack_v6_delay_th = params[4];
    var port = params[5]; // debug purpose

    var delta_client;
    if (status == "ipv4") delta_client = delta_t - a_delay_th/1000 - synack_v4_delay_th/1000;
    else if (status == "ipv6") delta_client = delta_t - aaaa_delay_th/1000 - synack_v6_delay_th/1000;
    delta_client = ~~(delta_client*1000)/1000; // round to 3 digits

    var text = ts  + " " + status + " " + delta_t + "s " + " " + seed + 
        " (delays) A: " + a_delay_th + "ms AAAA: " + aaaa_delay_th + "ms " +
        " SYN-ACK/IPv4: " + synack_v4_delay_th + "ms SYN-ACK/IPv6: " + synack_v6_delay_th + "ms ";

    var $div = $("<div>", {class: "log"} );
    $div.addClass(status);
    $div.text(text);
    $("#query_log").prepend($div);
}

HH.assert_dualstack = function() {
    $.when(HH.test_stack("ipv4")).fail(function(a1) {
        $( "#assert_dualstack" ).hide();
        HH.alert("<strong>ERROR</strong>: No IPv4 detected. Possible causes: you are not dual-stacked, the test server is down or you're behind a firewall.", "danger");
    }).done(function(a1) {
        $.when(HH.test_stack("ipv6")).done(function(a2) {
            $( "#assert_dualstack" ).hide();
            $( "#main_container" ).show();
            HH.reset();
        }).fail(function(a2) {
            $( "#assert_dualstack" ).hide();
            HH.alert("<strong>ERROR</strong>: No IPv6 detected. Possible causes: you are not dual-stacked, the test server is down or you're behind a firewall.", "danger");
        });
    });
}

HH.test_stack = function(ipversion) {
    var url = "http://test." + ipversion + "." + HH.main_url+":10000/ip";
    return $.ajax({
        "type" : 'GET',
        "dataType" : 'jsonp',
        "url": url,
        "cache": false,
        "pageCache":false,
        "timeout": 4000,
        "success": function(res) {},
        "error": function(d, msg) {},
        "complete": function() {}
    });
}

HH.test_json = function(results={}) {
    if (HH.run == 0) return;

    var params = HH.get_params();
    var seed = params[0];
    var a_delay_th = params[1];
    var aaaa_delay_th = params[2];
    var synack_v4_delay_th = params[3];
    var synack_v6_delay_th = params[4];
    var port = params[5];
    var test_url = params[6];

    var delay_max = Math.max(a_delay_th, aaaa_delay_th, synack_v4_delay_th, synack_v6_delay_th);

    var start_time = HH.getms();
    var status = "in progress";  

    var delta, rtt;
    $.ajax({
        "type" : 'GET',
        "callback": "callback",
        "dataType" : 'jsonp',
        "url": test_url,
        "cache": true,
        "pageCache":false,
        "timeout": HH.timeout + 100,
        "success": function(ipinfo) {
            delta = HH.getms() - start_time;
            status = ipinfo.type;
            rtt = ipinfo.rtt;
            document.getElementById("rtt_"+status).innerHTML = rtt+"ms";
        },
        "error": function(){
            /*
             * Note that in case of timeout, jquery will abort its request,
             * and delete the callback function it set up earlier
             * (something like jQuery123456789_09761234). This causes an
             * error when the request eventually arrives, because the
             * callback is no longer defined. Typically:
             *      ReferenceError: jQuery123456789_09761234 is not defined
             */
            delta = HH.getms() - start_time;
            if (delta > HH.timeout) {
                status="timeout";
                if (HH.tries.timeout > 20 && HH.run == 1) {
                    HH.stop()
                    console.log("Too many timeouts, aborting.");
                    HH.alert("<strong>WARNING</strong>: Too many timeouts encountered, aborting.", "warning");
                }
            } else {
                status="error";
            }
        },
        "complete": function() {
            var ts, delta_t;
            ts = new Date(start_time).toLocaleTimeString('en-US')
            delta_t = (~~delta)/1000;
            HH.tries[status] = HH.tries[status] + 1;
            HH.times[status].push(delta);
            HH.display_stats();

            results[status] += 1;

            HH.log_test(params, status, ts, delta_t);
        }
    });
};

HH.do_N_tests = function(N, results={}) {
    if (HH.run == 1) {
        for (i=0; i<N; i++)  HH.test_json(results);
    }
}

HH.auto_sweep = function(type, low, high, number_of_tests, step, from, looping, sign, r_number, r_interval) {
    /*
     * from can be "down" or "up": it reflects whether the value
     * has been increased or decreased since the previous time
     *
     * low and high estimate the threshold we are looking for
     *
     * looping is the number of "loop" we have done between
     * low and high, that is eg. low=50 and high=51, 50 -> 51 and then
     * 51 -> 50 is 1 loop
     *
     * sign is +1 or -1, and allows to reverse the logical order
     * If sign is -1, going "up" means going larger in negative (reverse order)
     * If sign is +1, going "up" means going larger in positive (logical order)
     *
     * We will make r_number requests every r_interval ms
     *
     * We stop the process when we make 2 loops in a row, without
     * low and high changing (too much). That is, if we thought the edge value
     * was between 50 and 51, do 50 -> 51, then 51 -> 50 and then
     * 50 -> 49, looping is now 1.5.
    */
    HH.reset_table();
    var results = {ipv4:0, ipv6:0, timeout:0};
    var FACTOR = 0.5; // multiplicative factor
    var delay = ~~(document.getElementById(type).value);

    HH.interval = setInterval(function() {HH.do_N_tests(r_number, results);}, r_interval); 

    var wait_for_completion = setInterval(function() {
        if (results["ipv6"]+results["ipv4"] >= number_of_tests) {
            clearInterval(HH.interval);
            clearInterval(wait_for_completion);

            var frac_ipv6 = 100.0*results["ipv6"]/(results["ipv6"]+results["ipv4"]);
            HH.addDataToGraph(delay, frac_ipv6);

            if (from == "down" && frac_ipv6 > 90) {
                if (sign == 1) HH.graph_stats.options.scales.xAxes[0].ticks.min = delay;
                else if (sign == -1) HH.graph_stats.options.scales.xAxes[0].ticks.max = delay;
            } else if (from == "up" && frac_ipv6 < 10) {
            // } else if (((from == "up" && sign == 1) || (sign == -1 && from == "down") ) && frac_ipv6 < 10) {
                if (sign == 1) HH.graph_stats.options.scales.xAxes[0].ticks.max = delay;
                else if (sign == -1) HH.graph_stats.options.scales.xAxes[0].ticks.min = delay;
            }

            // wait for a reasonable time to receive maybe other data
            setTimeout(function() {
                if (results["ipv6"] > results["ipv4"]) {
                    if (from == "up") {
                        step = (~~(step*FACTOR) == 0) ? 1 : ~~(FACTOR*step);
                        if (low-1 <= delay && delay <= low+1) looping += 0.5; else looping = 0;
                        low = delay;
                    }
                    delay += step*sign;
                    from = "down";
                } else if (results["ipv6"] < results["ipv4"]) {
                    if (from == "down") {
                        step = (~~(step*FACTOR) == 0) ? 1 : ~~(FACTOR*step);
                        if (high-1 <= delay && delay <= high+1) looping += 0.5; else looping = 0;
                        high = delay;
                    }
                    delay -= step*sign;
                    from = "up";
                }
                document.getElementById(type).value = delay;
                if (delay > high) high = delay;
                if (delay < low) low = delay;

                var more_tests = 100/(high+1-low);
                if (more_tests > number_of_tests) number_of_tests = ~~more_tests;

                if (looping >= 2) {
                    HH.stop();
                    HH.alert("<strong>RESULT</strong>: Threshold for " + type +" lies between "+low+" and "+high+" ms", "info");
                } else if (HH.run == 1) {
                    HH.auto_sweep(type, low, high, number_of_tests, step, from, looping, sign, r_number, r_interval);
                }
            }, 250+r_interval); // TODO: think more about this figure
        }
    }, 500+r_interval+Math.abs(delay)); // TODO: think more about this figure
}

HH.start_auto_sweep = function(type, sign) {
    // set everything back to zero
    HH.reset();
    HH.reset_delays();
    HH.disengage_buttons();
    HH.disengage_params();
    HH.run = 1;

    var tmp = HH.get_frequency();
    var r_number = tmp[0], r_interval = tmp[1];

    HH.show_graph();
    HH.auto_sweep(type, -1500, 1500, 13, 100, "down", 0, sign, r_number, r_interval);
}

HH.start_stop = function() {
    if (HH.run == 0) HH.start()
    else HH.stop();
};
