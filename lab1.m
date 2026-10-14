%% lab1.m — Lab I.1: Identification of the coupled DC motors (step inputs)
% Model:  G(s) = W(s)/U(s) = K / (tau*s + 1)   <=>   dw/dt = -a*w + b*u,
%         a = 1/tau (pole),  b = K/tau          (form used later for MIT / MRAC)
%
% Firmware: lab1/motor_io/motor_io.ino  (run lab1/circuit_check.m first)
% For each PWM in PWM_LIST: motor at rest -> step to PWM -> record.
%   - steady-state velocity  -> table (pwm, w_ss)  -> gain K
%   - rise time / tau        -> table (pwm, tau)   -> pole a = 1/tau
clear; clc; close all;

%% ---------- CONFIG ----------
PORT     = "";          % "" = auto-detect, or "/dev/ttyACM0" / "COM8"
BAUD     = 115200;
VSUPPLY  = 5;           % V = PWM*VSUPPLY/255 (lab convention)
% Pick values above the deadzone found by circuit_check.m
PWM_LIST = [-250 -225 -200 -175 -150 -125  125 150 175 200 225 250];
T_PRE    = 0.5;         % s recorded at PWM = 0 before the step
T_STEP   = 5;           % s recorded after the step
T_REST   = 3;           % s to let the motor stop between tests
POT_TAG  = "nom";       % label for the potentiometer position (min/nom/max)
% --------------------------------------------------------

%% Experiment
if PORT == ""
    ports = serialportlist("available");
    ports = ports(contains(ports, ["ttyACM", "ttyUSB", "COM", "usbmodem"]));  % skip /dev/ttyS*
    if isempty(ports), error("No Arduino port found (ttyACM/ttyUSB). Is it plugged in?"); end
    PORT = ports(end);
end
s = serialport(PORT, BAUD, "Timeout", 2);
configureTerminator(s, "LF");
cleanupObj = onCleanup(@() writeline(s, "S"));
pause(2.5);

runs = struct("pwm", {}, "t", {}, "u", {}, "w", {});
for k = 1:numel(PWM_LIST)
    p = PWM_LIST(k);
    fprintf("Step %2d/%d : PWM = %+4d\n", k, numel(PWM_LIST), p);
    writeline(s, "S"); pause(T_REST); flush(s);
    d0 = collect(s, T_PRE);
    writeline(s, "P" + p);
    d1 = collect(s, T_STEP);
    writeline(s, "S");
    d = [d0; d1];
    tStep = d(find(d(:, 2) == p, 1), 1);           % first sample with u = p
    runs(k).pwm = p;
    runs(k).t   = (d(:, 1) - tStep) / 1000;        % t = 0 at the step
    runs(k).u   = d(:, 2);
    runs(k).w   = d(:, 4);
end
writeline(s, "S");
clear cleanupObj s

%% Analysis: steady state, rise time, tau for each step
n = numel(runs);
[w_ss, tau, tr, td] = deal(zeros(n, 1));
for k = 1:n
    t = runs(k).t;  w = runs(k).w;
    ws = movmean(w, 5);                            % 100 ms smoothing (20 ms quantization)
    w_ss(k) = mean(w(t > T_STEP - 2));             % last 2 s

    % 10-90 % rise time on the smoothed signal
    i10 = find(t >= 0 & abs(ws) >= 0.1 * abs(w_ss(k)), 1);
    i90 = find(t >= 0 & abs(ws) >= 0.9 * abs(w_ss(k)), 1);
    if isempty(i10) || isempty(i90), tr(k) = NaN; else, tr(k) = t(i90) - t(i10); end

    % LS fit of w = w_ss*(1 - exp(-(t-td)/tau)) on the raw data -> [tau, td]
    m = t >= 0;
    cost = @(x) sum((w(m) - stepModel(t(m), w_ss(k), x(1), x(2))).^2);
    x = fminsearch(cost, [max(tr(k) / 2.2, 0.1), 0.02]);
    tau(k) = abs(x(1));  td(k) = max(x(2), 0);
end
pwm = [runs.pwm]';
V   = pwm * VSUPPLY / 255;
T1  = table(pwm, V, w_ss, tr, tau, td, ...
    'VariableNames', {'PWM', 'V', 'w_ss_RPM', 'tr_10_90_s', 'tau_fit_s', 'deadtime_s'});
disp(T1);

%% Gain: w_ss = K*(u - u0) separately for u > 0 and u < 0 (deadzone u0)
pos = pwm > 0;  neg = pwm < 0;
cP = polyfit(pwm(pos), w_ss(pos), 1);              % w = cP(1)*u + cP(2)
cN = polyfit(pwm(neg), w_ss(neg), 1);
K_pos = cP(1);  u0_pos = -cP(2) / cP(1);
K_neg = cN(1);  u0_neg = -cN(2) / cN(1);
K_all = pwm \ w_ss;                                % through the origin (pure 1st order)

%% Pole
tau_m = mean(tau);
a = 1 / tau_m;
b = K_all / tau_m;

fprintf("\n================ Lab I.1 results (pot = %s) ================\n", POT_TAG);
fprintf("  K (u>0)        = %.4f RPM/PWM   deadzone u0 = %+.1f PWM\n", K_pos, u0_pos);
fprintf("  K (u<0)        = %.4f RPM/PWM   deadzone u0 = %+.1f PWM\n", K_neg, u0_neg);
fprintf("  K (through 0)  = %.4f RPM/PWM  = %.3f RPM/V\n", K_all, K_all * 255 / VSUPPLY);
fprintf("  tau            = %.3f s  (std %.3f s,  tr/2.2 = %.3f s)\n", tau_m, std(tau), mean(tr, "omitnan") / 2.2);
fprintf("  pole           = -a = %.3f rad/s\n", -a);
fprintf("  G(s) = %.4f / (%.3f s + 1)      dw/dt = -%.3f w + %.4f u\n", K_all, tau_m, a, b);
fprintf("==============================================================\n");

%% Save (lab1/export_excel.m turns these files into the Excel tables)
model = struct("pot", POT_TAG, "K_pos", K_pos, "u0_pos", u0_pos, "K_neg", K_neg, ...
    "u0_neg", u0_neg, "K_all", K_all, "tau", tau_m, "tau_std", std(tau), "a", a, "b", b);
if ~exist("lab1/data", "dir"), mkdir("lab1/data"); end
stamp = string(datetime("now", "Format", "yyyyMMdd_HHmmss"));
save("lab1/data/steps_" + POT_TAG + "_" + stamp + ".mat", "runs", "T1", "model", "PWM_LIST", "VSUPPLY");

%% Plots
figure("Name", "Step responses");
tiledlayout("flow");
for k = 1:n
    nexttile;
    plot(runs(k).t, runs(k).w, ".", "Color", [0.6 0.6 0.6]); hold on;
    tt = linspace(0, T_STEP, 400);
    plot(tt, stepModel(tt, w_ss(k), tau(k), td(k)), "LineWidth", 1.5);
    grid on; title(sprintf("PWM %+d  (\\tau = %.2f s)", pwm(k), tau(k)));
    xlabel("t [s]"); ylabel("\omega [RPM]");
end

figure("Name", "Static map and time constant");
subplot(1, 2, 1);
plot(pwm, w_ss, "o", "MarkerFaceColor", "auto"); hold on; grid on;
uu = linspace(min(pwm), max(pwm), 200);
plot(uu(uu > 0), polyval(cP, uu(uu > 0)), "-", uu(uu < 0), polyval(cN, uu(uu < 0)), "-");
plot(uu, K_all * uu, "k--");
xlabel("PWM"); ylabel("\omega_{ss} [RPM]"); title("Steady-state velocity");
legend("data", "fit u>0", "fit u<0", "K through 0", "Location", "northwest");
subplot(1, 2, 2);
plot(pwm, tau, "s", "MarkerFaceColor", "auto"); hold on; grid on;
yline(tau_m, "--", sprintf("mean %.2f s", tau_m));
xlabel("PWM"); ylabel("\tau [s]"); title("Time constant");

%% ===================== local functions =====================
function y = stepModel(t, wss, tau, td)
    y = wss * (1 - exp(-max(t - td, 0) / max(abs(tau), 1e-3)));
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
