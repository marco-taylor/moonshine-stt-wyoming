<?php
// Read-only validation with the installed Unraid parser. Never execute returned commands.
declare(strict_types=1);
$subnet = ['bridge' => []];
$driver = ['bridge' => 'bridge'];
$docroot = '/usr/local/emhttp';
$var = ['timeZone' => 'Europe/Berlin', 'NAME' => 'Phase7-Validation'];
require '/usr/local/emhttp/plugins/dynamix.docker.manager/include/Helpers.php';
$template = dirname(__DIR__).'/templates/moonshine-stt-wyoming.xml';
$parsed = xmlToVar($template);
$command = xmlToCommand($template, false); // false: never mkdir/chown/chgrp host paths.
if ($parsed['Network'] !== 'bridge' || $parsed['Privileged'] !== 'false') {
    throw new RuntimeException('Unexpected network or privilege mode');
}
$env = [];
foreach ($parsed['Config'] as $config) {
    if ($config['Type'] === 'Variable') $env[$config['Target']] = $config['Value'];
}
foreach (['MOONSHINE_MODEL'=>'small-streaming-de', 'MOONSHINE_THREADS'=>'1',
          'MOONSHINE_AUTO_DOWNLOAD'=>'1', 'WYOMING_PORT'=>'10300',
          'WYOMING_STT_CONCURRENT_REQUESTS'=>'1', 'MOONSHINE_LANGUAGE'=>'de',
          'MOONSHINE_MODEL_DIR'=>'/app/models'] as $name=>$value) {
    if (($env[$name] ?? null) !== $value) throw new RuntimeException('Incorrect default: '.$name);
}
if (str_contains($command[0], 'small-streaming-de|tiny-streaming-de')) {
    throw new RuntimeException('Dropdown options leaked into command');
}
echo json_encode(['parser'=>'installed Unraid xmlToVar/xmlToCommand', 'create_paths'=>false,
                 'passed'=>true, 'config_count'=>count($parsed['Config']), 'environment'=>$env,
                 'planned_command_not_executed'=>$command[0]], JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES)."\n";
