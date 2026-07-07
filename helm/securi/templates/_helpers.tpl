{{- define "securi.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "securi.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "securi.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "securi.labels" -}}
helm.sh/chart: {{ include "securi.chart" . }}
{{ include "securi.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: securi
{{- end }}

{{- define "securi.selectorLabels" -}}
app.kubernetes.io/name: {{ include "securi.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "securi.configMapName" -}}
{{- printf "%s-config" (include "securi.fullname" .) }}
{{- end }}

{{- define "securi.secretName" -}}
{{- if .Values.secrets.existingSecret }}
{{- .Values.secrets.existingSecret }}
{{- else }}
{{- printf "%s-secrets" (include "securi.fullname" .) }}
{{- end }}
{{- end }}

{{- define "securi.postgresHost" -}}
{{- printf "%s-postgres" (include "securi.fullname" .) }}
{{- end }}

{{- define "securi.redisHost" -}}
{{- printf "%s-redis" (include "securi.fullname" .) }}
{{- end }}

{{- define "securi.databaseUrl" -}}
{{- if .Values.secrets.databaseUrl }}
{{- .Values.secrets.databaseUrl }}
{{- else if .Values.postgresql.enabled }}
{{- printf "postgresql+asyncpg://%s:%s@%s:5432/%s" .Values.postgresql.auth.username .Values.secrets.postgresPassword (include "securi.postgresHost" .) .Values.postgresql.auth.database }}
{{- else }}
{{- required "secrets.databaseUrl is required when postgresql.enabled is false" .Values.secrets.databaseUrl }}
{{- end }}
{{- end }}
