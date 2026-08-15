const DESKTOP_ENVIRONMENT_KEYS = new Set(
	[
		"APPDATA",
		"CI",
		"COLORTERM",
		"COMSPEC",
		"COREPACK_HOME",
		"DBUS_SESSION_BUS_ADDRESS",
		"DISPLAY",
		"FORCE_COLOR",
		"HOME",
		"HOMEDRIVE",
		"HOMEPATH",
		"LANG",
		"LANGUAGE",
		"LOCALAPPDATA",
		"LOGNAME",
		"NO_COLOR",
		"NPM_CONFIG_CACHE",
		"PATH",
		"PATHEXT",
		"PNPM_HOME",
		"PNPM_STORE_DIR",
		"PNPM_STORE_PATH",
		"SHELL",
		"SYSTEMROOT",
		"TEMP",
		"TERM",
		"TMP",
		"TMPDIR",
		"TZ",
		"USER",
		"USERNAME",
		"USERPROFILE",
		"WAYLAND_DISPLAY",
		"WINDIR",
		"XDG_CACHE_HOME",
		"XDG_CONFIG_HOME",
		"XDG_DATA_HOME",
		"XDG_RUNTIME_DIR",
		"__CF_USER_TEXT_ENCODING",
	].map((key) => key.toUpperCase()),
);

function isAllowedDesktopKey(key) {
	const normalized = key.toUpperCase();
	return (
		DESKTOP_ENVIRONMENT_KEYS.has(normalized) || normalized.startsWith("LC_")
	);
}

function desktopParentEnvironment(parentEnvironment) {
	return Object.fromEntries(
		Object.entries(parentEnvironment).filter(
			([key, value]) => value !== undefined && isAllowedDesktopKey(key),
		),
	);
}

export function createDevChildEnvironments(
	parentEnvironment,
	{ apiToken, apiBaseUrl, host, port },
) {
	const capabilityEnvironment = {
		VIKRAM_API_TOKEN: apiToken,
		VIKRAM_API_BASE_URL: apiBaseUrl,
	};
	return {
		apiEnvironment: {
			...parentEnvironment,
			...capabilityEnvironment,
			VIKRAM_HOST: host,
			VIKRAM_PORT: port,
		},
		desktopEnvironment: {
			...desktopParentEnvironment(parentEnvironment),
			...capabilityEnvironment,
		},
	};
}
