<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">

<html xmlns="http://www.w3.org/1999/xhtml" lang="en" xml:lang="en">
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <title>Test your Happy Eyeballs</title>
        <link rel="stylesheet" href="bootstrap-3.3.7-dist/css/bootstrap.min.css" type="text/css" />
        <link rel="stylesheet" href="index.css" type="text/css" />
        <script type="text/javascript" src="jquery-3.2.1.min.js"></script>
        <script type="text/javascript" src="jquery.jsonp-2.4.0.min.js"></script>
        <script type="text/javascript" src="bootstrap-3.3.7-dist/js/bootstrap.min.js"></script>
        <script type="text/javascript" src="index.js"></script>
    </head>
    <body>
        <nav class="navbar navbar-inverse navbar-fixed-top">
            <div class="container">
                <div class="navbar-header">
                    <button type="button" class="navbar-toggle collapsed" data-toggle="collapse" data-target="#navbar" aria-expanded="false" aria-controls="navbar">
                        <span class="sr-only">Toggle navigation</span>
                        <span class="icon-bar"></span>
                        <span class="icon-bar"></span>
                        <span class="icon-bar"></span>
                    </button>
                </div>
                <div id="navbar" class="collapse navbar-collapse">
                    <ul class="nav navbar-nav">
                        <li><a class="navbar-brand normal" href="http://ds.ds.6cn-prs.6cn.io">Experiment</a></li>
                        <li><a class="normal" href="http://stats.ds.6cn-prs.6cn.io">Stats</a></li>
                        <li class="active"><a class="normal" href="">Advanced</a></li>
                    </ul>
                </div><!--/.nav-collapse -->
            </div>
        </nav>

        <div class="container" id="main">
            <h1 id="title" style="margin-bottom:0;">Advanced</h1>
            <p>If the tests offerred via the front-end website is not enough for what you want to do, you can directly contact the webserver and
            make a simple script to do your testing.
            If you don't like calculations/are in a hurry/are lazy, use the tool below. <tt>:-)</tt></p>
            <p>
            <div class="row">
                <div class="col-sm-3">
                    A delay: <input type="number" class="param_input" id="a_delay" value="0">
                </div>
                <div class="col-sm-3">
                    AAAA delay: <input type="number" class="param_input" id="aaaa_delay" value="0">
                </div>
                <div class="col-sm-6">
                    SYN-ACK delay: <input type="number" class="param_input" id="syn_ack_delay" value="0"> (<0 means over IPv6, >0 means over IPv4)
                </div>
            </div>
            </p>
            <p id="url_result" class="bg-primary text-center">seed-0-0.test.ds.6cn-prs.6cn.io:10000/ip?callback=test</p>
            <hr />
            <h3>Explanations</h3>
            <p>To specify the delays you want, you have to correctly format the URL you use: <i>seed</i>-<i>A delay</i>-<i>AAAA delay</i>.test.ds.6cn-prs.6cn.io:<i>port</i>/ip?callback=test.</p>
            <h4>DNS delays</h4>
            Replace <i>A delay</i> and <i>AAAA delay</i> by the delay you want to be applied (in ms). <i>seed</i> can be whatever you want: if you change it every request, you will make a new DNS request every time. Depending on what you want to test, think about it.</p>
            <h4>SYN-ACK delay</h4>
            <p>As for the SYN-ACK delays, you have to use the appropriate distant port depending on the protocol. You cannot delay at the same time both the IPv4 and the IPv6 SYN-ACK, you have to choose one. The following table will help you choosing the right port for the delay you want:</p>
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th rowspan="2"></th>
                        <th class="text-center" colspan="2">Delay to apply (in ms)</th>
                        <th class="text-center" colspan="2">Port to contact</th>
                        <th class="text-center" style="vertical-align: middle;" rowspan="2">Granularity</th>
                        <th class="text-center" style="vertical-align: middle;" rowspan="2">Formula</th>
                    </tr>
                    <tr>
                        <th>From</th>
                        <th>To</th>
                        <th>From</th>
                        <th>To</th>
                    </tr>
                </thead>

                <tbody>
                    <tr>
                        <td class="text-center" style="vertical-align: middle;" rowspan="3"><b>IPv4</b></td>
                        <td>0</td>
                        <td>600</td>
                        <td>10,000</td>
                        <td>10,300</td>
                        <td>2</td>
                        <td>port = 10,000 + delay/2</td>
                    </tr>
                    <tr>
                        <td>600</td>
                        <td>1000</td>
                        <td>10,300</td>
                        <td>10,400</td>
                        <td>4</td>
                        <td>port = 10,300 + (delay-600)/4</td>
                    </tr>
                    <tr>
                        <td>1000</td>
                        <td>2980</td>
                        <td>10,400</td>
                        <td>10,499</td>
                        <td>20</td>
                        <td>port = 10,400 + (delay-1000)/20</td>
                    </tr>
                    <tr style="border-top:2px solid black">
                        <td class="text-center" style="vertical-align: middle;" rowspan="3"><b>IPv6</b></td>
                        <td>0</td>
                        <td>600</td>
                        <td>10,500</td>
                        <td>10,800</td>
                        <td>2</td>
                        <td>port = 10,500 + delay/2</td>
                    </tr>
                    <tr>
                        <td>600</td>
                        <td>1000</td>
                        <td>10,800</td>
                        <td>10,900</td>
                        <td>4</td>
                        <td>port = 10,800 + (delay-600)/4</td>
                    </tr>
                    <tr>
                        <td>1000</td>
                        <td>2980</td>
                        <td>10,900</td>
                        <td>10,999</td>
                        <td>20</td>
                        <td>port = 10,900 + (delay-1000)/20</td>
                    </tr>
                </tbody>
            </table>
        </div>
<script type="text/javascript">
var $a_delay = $('#a_delay');
var $aaaa_delay = $('#aaaa_delay');
var $syn_ack_delay = $('#syn_ack_delay');
var $result = $('#url_result');
function delay_to_port(delay) {
    var port;
    var delay_ipv6 = delay<0;
    delay = ~~Math.abs(delay);

    if (delay <= 600) delta_port = ~~(delay/2);
    else if (delay <= 1000) delta_port = 300 + ~~((delay-600)/4);
    else if (delay < 3000) delta_port = 400 + ~~((delay-1000)/20);
    else delta_port = 499; // the max we allow

    if (delay_ipv6) {
        // delay IPv6
        port = 10500+delta_port;
    } else {
        // delay IPv4
        port = 10000+delta_port;
    }

    return port;
}

function generate_url() {
    var port = delay_to_port($syn_ack_delay.val());
    url = "seed-" + $a_delay.val() + "-" + $aaaa_delay.val() + ".test.ds.6cn-prs.6cn.io:" + port + "/ip?callback=change_me";
    $result.text(url);
}

$a_delay.bind('input', generate_url);
$aaaa_delay.bind('input', generate_url);
$syn_ack_delay.bind('input', generate_url);
</script>
    </body>
</html>
