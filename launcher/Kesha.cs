// Kesha.exe: маленький запускатор. Собирается один раз (launcher\build.bat), а запускает
// свежий main.py системным pythonw.exe, поэтому правки .py пересборки не требуют.
// Иконка на панели задач одна: окно Кеши и ярлык «Кеша» в Пуске имеют один AppUserModelID
// (его ставит main.py, ярлыки делает tools\install_shortcuts.py).
using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

static class Kesha
{
    [STAThread]
    static int Main(string[] args)
    {
        string dir = AppDomain.CurrentDomain.BaseDirectory;
        string main = Path.Combine(dir, "main.py");
        if (!File.Exists(main))
            return Fail("Не нашёл main.py рядом с Kesha.exe:\n" + dir);

        string python = FindPythonw();
        if (python == null)
            return Fail("Не нашёл pythonw.exe. Задай путь в переменной KESHA_PYTHON.");

        var psi = new ProcessStartInfo(python, "\"" + main + "\" " + string.Join(" ", args))
        {
            WorkingDirectory = dir,
            UseShellExecute = false,
        };
        Process.Start(psi);
        return 0;
    }

    static string FindPythonw()
    {
        string env = Environment.GetEnvironmentVariable("KESHA_PYTHON");
        if (!string.IsNullOrEmpty(env) && File.Exists(env)) return env;
        string local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        foreach (string ver in new[] { "Python313", "Python314", "Python312" })
        {
            string p = Path.Combine(local, "Programs", "Python", ver, "pythonw.exe");
            if (File.Exists(p)) return p;
        }
        foreach (string d in (Environment.GetEnvironmentVariable("PATH") ?? "").Split(';'))
        {
            try
            {
                string p = Path.Combine(d.Trim(), "pythonw.exe");
                if (File.Exists(p) && !p.Contains("WindowsApps")) return p;   // заглушка Microsoft Store не годится
            }
            catch (ArgumentException) { }
        }
        return null;
    }

    static int Fail(string msg)
    {
        MessageBox.Show(msg, "Кеша", MessageBoxButtons.OK, MessageBoxIcon.Error);
        return 1;
    }
}
