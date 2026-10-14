%% circuit_check.m — Check the coupled DC motor circuit (Adaptive Control Lab)
% Upload lab1/motor_io/motor_io.ino to the Arduino Mega first, close the
% Arduino Serial Monitor, then run this script.
%
% Tests:
%   1. Serial link       - Arduino answers and streams data
%   2. Encoder at rest   - no counts while motor is off (noise / loose wire)
%   3. Encoder by hand   - one turn by hand ~ PPR counts, sign follows direction
%   4. Forward drive     - +PWM gives positive RPM
%   5. Reverse drive     - -PWM gives negative RPM, similar magnitude
%   6. Deadzone          - smallest |PWM| that moves the motor (both directions)
clear; clc; close all;

%% ---------- CONFIG ----------
PORT     = "";        % "" = auto-detect, or e.g. "/dev/ttyACM0" / "COM8"
BAUD     = 115200;
PPR      = 2150;      % counts per output revolution (same as Robust Lab)
PWM_TEST = 200;       % PWM used for the drive tests
T_DRIVE  = 4;         % seconds per drive test
% ----------------------------

if PORT == ""
    ports = serialportlist("available");
    ports = ports(contains(ports, ["ttyACM", "ttyUSB", "COM", "usbmodem"]));  % skip /dev/ttyS*
    if isempty(ports), error("No serial port found. Is the Arduino plugged in?"); end
    PORT = ports(end);
end
fprintf("Connecting to %s @ %d ...\n", PORT, BAUD);
s = serialport(PORT, BAUD, "Timeout", 2);
configureTerminator(s, "LF");
cleanupObj = onCleanup(@() stopMotor(s));
pause(2.5);                       % Arduino resets when the port opens
results = strings(0, 2);

%% 1. Serial link
flush(s);
d = collect(s, 0.5);
ok = size(d, 1) > 10;
results(end+1, :) = ["Serial link", verdict(ok, sprintf("%d samples in 0.5 s", size(d, 1)))];
if ~ok, printResults(results); error("No data from Arduino. Check sketch upload / port / baud."); end

%% 2. Encoder at rest
send(s, "S"); send(s, "Z"); pause(0.5); flush(s);
d = collect(s, 2);
drift = max(d(:, 3)) - min(d(:, 3));
results(end+1, :) = ["Encoder at rest", verdict(drift <= 2, sprintf("count drift = %d", drift))];

%% 3. Encoder by hand
fprintf("\n>> Mark the output shaft. Turn it ONE full turn by hand in the direction\n");
fprintf("   you want to call POSITIVE, then press Enter.\n");
send(s, "Z"); pause(0.2); flush(s);
input("", "s");
d = collect(s, 0.2);
handCounts = d(end, 3);
okHand = abs(abs(handCounts) - PPR) < 0.15 * PPR;
results(end+1, :) = ["Encoder 1 turn by hand", verdict(okHand, ...
    sprintf("%d counts (expected ~%s%d)", handCounts, char(177), PPR))];
handSign = sign(handCounts);

%% 4./5. Forward and reverse drive
send(s, "Z"); flush(s);
[tf, rf] = driveTest(s, +PWM_TEST, T_DRIVE);
[tr, rr] = driveTest(s, -PWM_TEST, T_DRIVE);
wF = mean(rf(tf > 2));   % steady state (after 2 s)
wR = mean(rr(tr > 2));
results(end+1, :) = ["Forward  +PWM -> +RPM", verdict(wF > 1, sprintf("%.2f RPM", wF))];
results(end+1, :) = ["Reverse  -PWM -> -RPM", verdict(wR < -1, sprintf("%.2f RPM", wR))];
sym = abs(wF / wR);
results(end+1, :) = ["Fwd/Rev symmetry", verdict(sym > 0.75 && sym < 1.33, sprintf("|wF/wR| = %.2f", sym))];
if handSign ~= 0
    results(end+1, :) = ["Hand dir == +PWM dir", verdict(handSign == sign(wF), ...
        "if FAIL: your 'positive' is the opposite of +PWM (only a convention)")];
end

%% 6. Deadzone (smallest |PWM| that moves the motor)
dzF = findDeadzone(s, +1);
dzR = findDeadzone(s, -1);
results(end+1, :) = ["Deadzone", sprintf("INFO  fwd ~%d PWM, rev ~%d PWM", dzF, dzR)];
send(s, "S");

%% Report
printResults(results);

figure("Name", "Circuit check");
plot(tf, rf, tf(end) + tr, rr); grid on;
yline([wF wR], "--");
xlabel("t [s]"); ylabel("\omega [RPM]");
legend(sprintf("PWM = +%d", PWM_TEST), sprintf("PWM = -%d", PWM_TEST), "Location", "best");
title("Forward / reverse drive test");

if any(contains(results(:, 2), "FAIL"))
    fprintf(["\nTroubleshooting:\n" ...
        " - Encoder at rest drifts      -> loose encoder wire / missing GND\n" ...
        " - Hand turn gives ~0 counts   -> encA not on pin 18, or encoder VCC/GND missing\n" ...
        " - Hand count always same sign -> encB not on pin 19\n" ...
        " - Forward gives negative RPM  -> swap the two motor leads (or encA/encB)\n" ...
        " - Motor does not move         -> driver supply / IA=5, IB=4 / common GND\n" ...
        " - Only one direction works    -> check the IA (pin 5) or IB (pin 4) wire\n"]);
end

%% ===================== local functions =====================
function send(s, cmd)
    writeline(s, cmd);
end

function stopMotor(s)
    try, writeline(s, "S"); catch, end
end

function d = collect(s, T)
% Read stream for T seconds -> [t_ms, pwm, count, rpm]
    d = zeros(0, 4);
    t0 = tic;
    while toc(t0) < T
        line = readline(s);
        if isempty(line) || ~startsWith(line, "D,"), continue; end
        v = str2double(split(extractAfter(line, 2), ","))';
        if numel(v) == 4 && all(~isnan(v)), d(end+1, :) = v; end %#ok<AGROW>
    end
end

function [t, rpm] = driveTest(s, pwm, T)
    send(s, "S"); pause(1.5); flush(s);
    send(s, "P" + pwm);
    d = collect(s, T);
    send(s, "S");
    t = (d(:, 1) - d(1, 1)) / 1000;
    rpm = d(:, 4);
end

function dz = findDeadzone(s, dir)
    dz = NaN;
    send(s, "S"); pause(1);
    for p = 0:5:255
        send(s, "P" + dir * p); pause(0.6); flush(s);
        d = collect(s, 0.6);
        if size(d, 1) > 1 && abs(d(end, 3) - d(1, 3)) > 20   % clearly moving
            dz = dir * p; break;
        end
    end
    send(s, "S"); pause(1);
end

function out = verdict(ok, msg)
    if ok, out = "PASS  " + msg; else, out = "FAIL  " + msg; end
end

function printResults(r)
    fprintf("\n===================== CIRCUIT CHECK =====================\n");
    for i = 1:size(r, 1)
        fprintf("  %-24s %s\n", r(i, 1), r(i, 2));
    end
    fprintf("=========================================================\n");
end
