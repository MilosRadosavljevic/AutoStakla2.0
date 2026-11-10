; Instalacija AutoStakla – pravi je build.ps1 (prosleđuje AppVersion, AppName, SourceDir, IconFile, OutDir)

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef AppName
  #define AppName "AutoStakla"
#endif

[Setup]
AppId={{6F1C7E2A-3B4D-4E8A-9C21-A57A0B1D2E44}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Miloš Radosavljević
DefaultDirName=C:\AutoStakla
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableWelcomePage=no
PrivilegesRequired=lowest
UsePreviousAppDir=no
OutputDir={#OutDir}
OutputBaseFilename={#AppName}_Setup_{#AppVersion}
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\app\AutoStakla.exe
UninstallDisplayName={#AppName}
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
AppMutex=AutoStaklaMutex
CloseApplications=no
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible

[Languages]
Name: "sr"; MessagesFile: "compiler:Default.isl"

[Messages]
SetupAppTitle=Instalacija
SetupWindowTitle=Instalacija – %1
ButtonBack=< &Nazad
ButtonNext=&Dalje >
ButtonInstall=&Instaliraj
ButtonOK=U redu
ButtonCancel=Otkaži
ButtonYes=&Da
ButtonYesToAll=Da za &sve
ButtonNo=&Ne
ButtonNoToAll=N&e za sve
ButtonFinish=&Završi
ButtonBrowse=&Pretraži...
ExitSetupTitle=Izlaz iz instalacije
ExitSetupMessage=Instalacija nije završena. Ako sada izađete, program neće biti instaliran.%n%nInstalaciju možete ponovo pokrenuti kasnije.%n%nIzaći iz instalacije?
SetupAppRunningError=Program %1 je trenutno pokrenut.%n%nZatvorite ga, pa kliknite U redu za nastavak, ili Otkaži za izlaz.
UninstallAppRunningError=Program %1 je trenutno pokrenut.%n%nZatvorite ga, pa kliknite U redu za nastavak, ili Otkaži za izlaz.
WelcomeLabel1=Dobro došli u instalaciju programa [name]
WelcomeLabel2=Na ovaj računar biće instaliran program [name/ver].%n%nProgram će biti u folderu C:\AutoStakla, a prečica na desktopu.%n%nPreporučuje se da zatvorite ostale programe pre nastavka.
WizardSelectTasks=Dodatne opcije
SelectTasksDesc=Šta još treba uraditi?
SelectTasksLabel2=Izaberite šta još treba uraditi, pa kliknite Dalje.
WizardReady=Spremno za instalaciju
ReadyLabel1=Sve je spremno za instalaciju programa [name].
ReadyLabel2a=Kliknite Instaliraj za početak, ili Nazad ako želite nešto da promenite.
ReadyLabel2b=Kliknite Instaliraj za početak.
ReadyMemoDir=Folder:
ReadyMemoTasks=Dodatne opcije:
WizardPreparing=Priprema instalacije
WizardInstalling=Instalacija
InstallingLabel=Sačekajte dok se program [name] instalira.
FinishedHeadingLabel=Instalacija je završena
FinishedLabelNoIcons=Program [name] je instaliran.
FinishedLabel=Program [name] je instaliran. Pokreće se preko prečice „AutoStakla" na desktopu.
ClickFinish=Kliknite Završi za kraj.
StatusExtractFiles=Kopiranje fajlova...
StatusCreateIcons=Pravljenje prečica...
StatusRunProgram=Završavanje instalacije...
StatusUninstalling=Uklanjanje programa %1...
ConfirmUninstall=Da li sigurno želite da uklonite %1?%n%nPodaci (baza i backup) u C:\AutoStakla NEĆE biti obrisani.
UninstalledAll=Program %1 je uklonjen.%n%nPodaci su ostali u folderu C:\AutoStakla\data i C:\AutoStakla\backup.
UninstallStatusLabel=Sačekajte dok se program %1 uklanja.
UninstallAppFullTitle=Uklanjanje – %1

[Dirs]
Name: "{app}\data";   Flags: uninsneveruninstall
Name: "{app}\backup"; Flags: uninsneveruninstall
Name: "{app}\logs";   Flags: uninsneveruninstall

[InstallDelete]
; ponovna instalacija – stari program se briše, podaci ostaju
Type: filesandordirs; Name: "{app}\app"
Type: filesandordirs; Name: "{app}\app_old"
Type: filesandordirs; Name: "{app}\update"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}\app"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userdesktop}\{#AppName}";  Filename: "{app}\app\AutoStakla.exe"; WorkingDir: "{app}\app"
Name: "{userprograms}\{#AppName}"; Filename: "{app}\app\AutoStakla.exe"; WorkingDir: "{app}\app"

[Run]
Filename: "{app}\app\AutoStakla.exe"; Description: "Pokreni {#AppName}"; WorkingDir: "{app}\app"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\app"
Type: filesandordirs; Name: "{app}\app_old"
Type: filesandordirs; Name: "{app}\update"
Type: files;          Name: "{app}\autostakla.lock"
