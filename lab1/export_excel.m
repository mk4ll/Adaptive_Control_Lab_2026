%% export_excel.m — Lab I.1 tables to Excel
% Reads the step-test files saved by lab1.m (lab1/data/steps_<pot>_<time>.mat)
% and writes lab1/Lab1_identification.xlsx with, per potentiometer position:
%   SteadyState_<pot> : input (PWM, V) vs steady-state velocity w   -> gain
%   RiseTime_<pot>    : input (PWM, V) vs rise time / tau           -> pole
%   Raw_<pot>         : the recorded step responses (t, w per PWM)
% and one Summary sheet comparing K, deadzone, tau, a, b across pot positions.
% If a pot position was measured more than once, the latest file is used.
clear; clc;

here    = fileparts(mfilename("fullpath"));
DATA    = fullfile(here, "data");
OUTFILE = fullfile(here, "Lab1_identification.xlsx");

files = dir(fullfile(DATA, "steps_*.mat"));
if isempty(files), error("No steps_*.mat in %s. Run lab1.m first.", DATA); end
[~, order] = sort({files.name});                   % timestamp in name -> chronological
files = files(order);

% latest file per potentiometer tag
latest = containers.Map();
for f = files'
    tok = regexp(f.name, "^steps_(.+)_\d{8}_\d{6}\.mat$", "tokens", "once");
    if ~isempty(tok), latest(tok{1}) = fullfile(f.folder, f.name); end
end

if isfile(OUTFILE), delete(OUTFILE); end
summary = table();
for tag = string(keys(latest))
    S = load(latest(tag));
    T1 = S.T1;

    steady = T1(:, {'PWM', 'V', 'w_ss_RPM'});
    rise   = T1(:, {'PWM', 'V', 'tr_10_90_s', 'tau_fit_s', 'deadtime_s'});
    writetable(steady, OUTFILE, "Sheet", "SteadyState_" + tag);
    writetable(rise,   OUTFILE, "Sheet", "RiseTime_" + tag);
    writecell(rawBlock(S.runs), OUTFILE, "Sheet", "Raw_" + tag);

    m = S.model;
    summary = [summary; table(string(tag), m.K_pos, m.u0_pos, m.K_neg, m.u0_neg, ...
        m.K_all, m.tau, m.tau_std, m.a, m.b, ...
        'VariableNames', {'pot', 'K_pos_RPM_per_PWM', 'deadzone_pos_PWM', ...
        'K_neg_RPM_per_PWM', 'deadzone_neg_PWM', 'K_through0_RPM_per_PWM', ...
        'tau_s', 'tau_std_s', 'a_1_per_s', 'b'})]; %#ok<AGROW>
    [~, name] = fileparts(latest(tag));
    fprintf("  %-6s <- %s\n", tag, name);
end
writetable(summary, OUTFILE, "Sheet", "Summary");
fprintf("\nSaved: %s\n", OUTFILE);
disp(summary);

%% ===================== local functions =====================
function C = rawBlock(runs)
% Side-by-side columns: t_PWM+200 | w_PWM+200 | t_PWM-200 | ...
    n = max(arrayfun(@(r) numel(r.t), runs));
    C = cell(n + 1, 2 * numel(runs));
    for k = 1:numel(runs)
        tag = sprintf("PWM%+d", runs(k).pwm);
        C{1, 2*k-1} = "t_s_" + tag;
        C{1, 2*k}   = "w_RPM_" + tag;
        C(2:numel(runs(k).t) + 1, 2*k-1) = num2cell(runs(k).t);
        C(2:numel(runs(k).w) + 1, 2*k)   = num2cell(runs(k).w);
    end
end
