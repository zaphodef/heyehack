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
        <script type="text/javascript" src="jstat.js"></script>
        <script type="text/javascript" src="Chart.js"></script>
        <script type="text/javascript" src="bootstrap-3.3.7-dist/js/bootstrap.min.js"></script>
        <script type="text/javascript" src="index.js"></script>
<?php

$running_file = "/var/run/heyehack/running";
$active = 0;
if (file_exists($running_file)) {
    $f = fopen($running_file, 'r');
    $val = fread($f, 1);
    fclose($f);
    if (isset($val) && ($val == '1')) $active = 1; 
}

$_SESSION['active'] = $active;

?>
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
                        <li class="active"><a class="navbar-brand normal" href="">Experiment</a></li>
                        <li><a class="normal"href="http://stats.ds.6cn-prs.6cn.io">Stats</a></li>
                    </ul>
                </div><!--/.nav-collapse -->
            </div>
        </nav>

        <div class="container" id="intro">
            <h1 id="title" style="margin-bottom:0;">HeyeHack</h1>

            <div id="introduction">
                <p>This is a test for Happy Eyeballs. It will repeatedly attempt to load, via this browser instance, a randomly
                named dual stack javascript resource. Below you will see counters of how often IPv6 is used, IPv4 is used, or both
                fail. You can interfere on some values in the <a href="#options">Params</a> section. If you want to see the
                threshold between "using IPv6" and "using IPv4", you can use the "auto sweep" functionality.</p>
            </div>
            
            <br/>
        </div>

        <div class="container" id="assert_dualstack">
            <div id="loader"></div>
            <div id="loading-text">Asserting you are dual-stacked. Please wait, this shouldn't take long.</div>
        </div>

        <div class="container" id="hh_alert"></div>
        
        <div class="container" id="main_container" style="display: none;">
            <div class="row">
                <div class="col-sm-6">
                    <div id="content">
                        <table class="table-condensed" border="1">
                            <thead>
                            <tr>
                                <th>Protocol</th>
                                <th>Count</th>
                                <th>Percentage</th>
                                <th>Average</th>
                                <th>Median</th>
                                <th>StdDev</th>
                                <th>RTT</th>
                            </tr>
                            </thead>

                            <tr class="ipv4">
                                <td>IPv4</td>
                                <td id="ipv4"></td>
                                <td id="percent_ipv4"></td>
                                <td id="average_ipv4"></td>
                                <td id="median_ipv4"></td>
                                <td id="stddev_ipv4"></td>
                                <td id="rtt_ipv4">no data</td>
                            </tr>

                            <tr class="ipv6">
                                <td>IPv6</td>
                                <td id="ipv6"></td>
                                <td id="percent_ipv6"></td>
                                <td id="average_ipv6"></td>
                                <td id="median_ipv6"></td>
                                <td id="stddev_ipv6"></td>
                                <td id="rtt_ipv6">no data</td>
                            </tr>

                            <tr class="error">
                                <td>Error (< 7s)</td>
                                <td id="error"></td>
                                <td id="percent_error"></td>
                                <td id="average_error"></td>
                                <td id="median_error"></td>
                                <td id="stddev_error"></td>
                                <td>N/A</td>
                            </tr>

                            <tr class="timeout">
                                <td>Timeout (> 7s)</td>
                                <td id="timeout"></td>
                                <td id="percent_timeout"></td>
                                <td id="average_timeout"></td>
                                <td id="median_timeout"></td>
                                <td id="stddev_timeout"></td>
                                <td>N/A</td>
                            </tr>
                        </table>
                    </div>
                    <div id="options">
                        <h3>
                        Params
                        <?php if ($_SESSION['active'] == 0) echo '<small><i>(handler inactive, check the server)</i></small>'; ?>
                        </h3>    
                        <p>Change DNS name every 
                        <span id="n_1" class="active"><a href="javascript:HH.random_after_N(1)">1</a></span>
                        |
                        <span id="n_10"><a href="javascript:HH.random_after_N(10)">10</a></span>
                        |
                        <span id="n_100000"><a href="javascript:HH.random_after_N(100000)">100000</a></span>
                        calls.
                        <form class="form-inline">
                            Send <input type="number" class="param_input" id="requests_number" value=1> request(s) every 
                            <input type="number" class="param_input" id="requests_delay" value=1000> ms.
                            <br />
                            Delay AAAA answers by
                            <input type="number" class="param_input" name="AAAA" id="aaaa_delay" value=0 <?php if ($_SESSION['active'] == 0) echo ' disabled'; ?>>
                            ms and A answers by
                            <input type="number" class="param_input" name="A" id="a_delay" value=0 <?php if ($_SESSION['active'] == 0) echo ' disabled'; ?>>
                            ms
                            <br />Delay SYN-ACK answers by 
                            <input type="number" class="param_input" name="SYN-ACK" id="synack_delay" value=0 <?php if ($_SESSION['active'] == 0) echo ' disabled'; ?>>
                             ms (negative means delay IPv6, positive means delay IPv4).
                            <br />
                        </form>
                    </div>
                </div>
                <div class="col-sm-6">
                    <div id="graph" style=""><canvas id="graph_stats" width="100%" height="55%"></canvas></div>
                </div>
            </div>
            <div class="buttons">
                <button class="btn btn-success" id="button_start_stop" onclick="HH.start_stop()">Start</button>
                <button class="btn btn-info" id="sweep_aaaa" onclick="HH.start_auto_sweep('aaaa_delay', 1)">Auto sweep AAAA</button>
                <button class="btn btn-info" id="sweep_synack" onclick="HH.start_auto_sweep('synack_delay', -1)">Auto sweep SYN-ACK</button>
            </div>

            <hr />
            <h3>Results</h3>
            <div id="query_log_container">
                <div id="query_log"></div>
            </div>

            <div id="noscript">
                <p>JavaScript required</p>
            </div>

            <script type="text/javascript">
HH.assert_dualstack();
jQuery("#noscript").hide();
            </script>

            <hr />
            <i>Sources are available under the MIT license <a href="https://github.com/zaphodef/heyehack">on GitHub</a>. This website is based on another website by Jason Fesler, see <a href="https://github.com/falling-sky/happy-eye-test">the appropriate GitHub repo</a>.</i>
        </div>
    </body>
</html>
