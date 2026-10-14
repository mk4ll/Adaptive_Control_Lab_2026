%% spin_test.m — Spin the motor at constant PWM with a live RPM plot
% Runs until you close the figure window, then stops the motor.
% Firmware: lab1/motor_io/motor_io.ino. Close the Arduino Serial Monitor first.
clear; clc; close all;

%% ---------- CONFIG ----------
PORT = "/dev/ttyACM0";
BAUD = 115200;
PWM  = 200;             % signed, -255..255
WIN  = 10;              % seconds shown in the plot
% ----------------------------

s = serialport(PORT, BAUD, "Timeout", 2);
configureTerminator(s, "LF");
cleanupObj = onCleanup(@() writeline(s, "S"));
pause(2.5);                                   % Arduino resets when the port opens
flush(s);
writeline(s, "P" + PWM);

fig = figure("Name", "Spin test — close window to stop");
h = animatedline("Color", [0 0.45 0.74], "MaximumNumPoints", WIN * 50);
grid on; xlabel("t [s]"); ylabel("\omega [RPM]");
t0 = [];
while isvalid(fig)
    line = readline(s);
    if isempty(line) || ~startsWith(line, "D,"), continue; end
    v = str2double(split(extractAfter(line, 2), ","));
    if numel(v) ~= 4 || any(isnan(v)), continue; end
    if isempty(t0), t0 = v(1); end
    t = (v(1) - t0) / 1000;
    addpoints(h, t, v(4));
    xlim([max(0, t - WIN), max(WIN, t)]);
    title(sprintf("PWM = %+d   \\omega = %.1f RPM   count = %d", v(2), v(4), v(3)));
    drawnow limitrate;
end
writeline(s, "S");
