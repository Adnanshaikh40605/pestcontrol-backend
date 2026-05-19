import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:provider/provider.dart';

import '../config/api_config.dart';
import '../core/api_client.dart';
import '../providers/auth_provider.dart';
import '../providers/profile_provider.dart';
import 'debug_config.dart';
import 'debug_dio_interceptor.dart';
import 'debug_log_store.dart';
import 'debug_models.dart';
import 'debug_utils.dart';

class DebugPanel {
  DebugPanel._();

  static void show(BuildContext context, {int initialTab = 0}) {
    if (!DebugConfig.enabled) return;
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: const Color(0xFF0D1117),
      builder: (ctx) => _DebugPanelSheet(initialTab: initialTab),
    );
  }
}

class _DebugPanelSheet extends StatefulWidget {
  const _DebugPanelSheet({required this.initialTab});

  final int initialTab;

  @override
  State<_DebugPanelSheet> createState() => _DebugPanelSheetState();
}

class _DebugPanelSheetState extends State<_DebugPanelSheet>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs;
  PackageInfo? _packageInfo;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 6, vsync: this, initialIndex: widget.initialTab);
    PackageInfo.fromPlatform().then((info) {
      if (mounted) setState(() => _packageInfo = info);
    });
    debugSyncGoRoute(GoRouter.of(context).state.uri.toString());
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final store = context.watch<DebugLogStore>();
    final height = MediaQuery.sizeOf(context).height * 0.88;

    return SizedBox(
      height: height,
      child: Column(
        children: [
          _Header(
            onCopy: () => _copyLogs(context),
            onClear: () => store.clear(),
          ),
          _FilterBar(
            filter: store.filter,
            onChanged: store.setFilter,
          ),
          _LiveBar(store: store),
          TabBar(
            controller: _tabs,
            isScrollable: true,
            labelColor: Colors.tealAccent,
            unselectedLabelColor: Colors.white54,
            indicatorColor: Colors.tealAccent,
            tabs: const [
              Tab(text: 'API'),
              Tab(text: 'Errors'),
              Tab(text: 'Requests'),
              Tab(text: 'Backend'),
              Tab(text: 'Auth'),
              Tab(text: 'Device'),
            ],
          ),
          Expanded(
            child: TabBarView(
              controller: _tabs,
              children: [
                _ApiLogsTab(requests: store.requests),
                _ErrorsTab(logs: store.filteredLogs),
                _RequestsTab(store: store),
                _BackendTab(requests: store.errorRequests),
                _AuthTab(),
                _DeviceTab(packageInfo: _packageInfo),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _copyLogs(BuildContext context) async {
    final text = DebugLogStore.instance.exportLogs();
    await Clipboard.setData(ClipboardData(text: text));
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Debug logs copied to clipboard')),
      );
    }
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.onCopy, required this.onClear});

  final VoidCallback onCopy;
  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 8, 8),
      child: Row(
        children: [
          const Icon(Icons.developer_mode, color: Colors.tealAccent),
          const SizedBox(width: 8),
          const Expanded(
            child: Text(
              'Debug Inspector',
              style: TextStyle(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          TextButton.icon(
            onPressed: onCopy,
            icon: const Icon(Icons.copy, size: 18, color: Colors.tealAccent),
            label: const Text('Copy', style: TextStyle(color: Colors.tealAccent)),
          ),
          IconButton(
            onPressed: onClear,
            icon: const Icon(Icons.delete_outline, color: Colors.white54),
            tooltip: 'Clear logs',
          ),
          IconButton(
            onPressed: () => Navigator.pop(context),
            icon: const Icon(Icons.close, color: Colors.white54),
          ),
        ],
      ),
    );
  }
}

class _FilterBar extends StatelessWidget {
  const _FilterBar({required this.filter, required this.onChanged});

  final DebugLogFilter filter;
  final ValueChanged<DebugLogFilter> onChanged;

  @override
  Widget build(BuildContext context) {
    const filters = DebugLogFilter.values;
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      child: Row(
        children: filters.map((f) {
          final selected = f == filter;
          return Padding(
            padding: const EdgeInsets.only(right: 8, bottom: 8),
            child: FilterChip(
              selected: selected,
              label: Text(_label(f), style: const TextStyle(fontSize: 12)),
              onSelected: (_) => onChanged(f),
              selectedColor: Colors.teal.withValues(alpha: 0.35),
              backgroundColor: const Color(0xFF21262D),
              labelStyle: TextStyle(color: selected ? Colors.white : Colors.white70),
            ),
          );
        }).toList(),
      ),
    );
  }

  String _label(DebugLogFilter f) => switch (f) {
        DebugLogFilter.all => 'All',
        DebugLogFilter.errorsOnly => 'Errors',
        DebugLogFilter.apiOnly => 'API',
        DebugLogFilter.warnings => 'Warnings',
        DebugLogFilter.navigation => 'Nav',
        DebugLogFilter.auth => 'Auth',
      };
}

class _LiveBar extends StatelessWidget {
  const _LiveBar({required this.store});

  final DebugLogStore store;

  @override
  Widget build(BuildContext context) {
    final net = store.network;
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xFF21262D),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Icon(
            net.isConnected ? Icons.wifi : Icons.wifi_off,
            size: 16,
            color: net.isConnected ? Colors.greenAccent : Colors.redAccent,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'Network: ${net.label} · In-flight: ${store.activeLoading}',
              style: const TextStyle(color: Colors.white70, fontSize: 12),
            ),
          ),
          if (store.pendingRequests.isNotEmpty)
            const SizedBox(
              width: 14,
              height: 14,
              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.tealAccent),
            ),
        ],
      ),
    );
  }
}

class _ApiLogsTab extends StatelessWidget {
  const _ApiLogsTab({required this.requests});

  final List<ApiRequestRecord> requests;

  @override
  Widget build(BuildContext context) {
    if (requests.isEmpty) {
      return const _EmptyState('No API calls yet');
    }
    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: requests.length,
      itemBuilder: (context, i) => _RequestTile(requests[i]),
    );
  }
}

class _ErrorsTab extends StatelessWidget {
  const _ErrorsTab({required this.logs});

  final List<DebugLogEntry> logs;

  @override
  Widget build(BuildContext context) {
    final errors = logs
        .where((l) => l.category == DebugLogCategory.error)
        .toList();
    if (errors.isEmpty) {
      return const _EmptyState('No errors captured');
    }
    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: errors.length,
      itemBuilder: (context, i) => _LogTile(errors[i]),
    );
  }
}

class _RequestsTab extends StatelessWidget {
  const _RequestsTab({required this.store});

  final DebugLogStore store;

  @override
  Widget build(BuildContext context) {
    final pending = store.pendingRequests;
    final recent = store.requests.take(30).toList();

    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        if (pending.isNotEmpty) ...[
          const Text('LOADING', style: TextStyle(color: Colors.amber, fontSize: 12)),
          const SizedBox(height: 8),
          ...pending.map(_RequestTile.new),
          const SizedBox(height: 16),
        ],
        const Text('HISTORY', style: TextStyle(color: Colors.white54, fontSize: 12)),
        const SizedBox(height: 8),
        ...recent.map(_RequestTile.new),
      ],
    );
  }
}

class _BackendTab extends StatelessWidget {
  const _BackendTab({required this.requests});

  final List<ApiRequestRecord> requests;

  @override
  Widget build(BuildContext context) {
    if (requests.isEmpty) {
      return const _EmptyState('No backend errors (4xx/5xx)');
    }
    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: requests.length,
      itemBuilder: (context, i) {
        final r = requests[i];
        return Card(
          color: const Color(0xFF21262D),
          child: ExpansionTile(
            title: Text(
              '${r.statusCode} ${r.method}',
              style: TextStyle(
                color: r.statusCode == 401 ? Colors.orange : Colors.redAccent,
                fontWeight: FontWeight.w600,
              ),
            ),
            subtitle: Text(r.url, style: const TextStyle(fontSize: 11, color: Colors.white54)),
            children: [
              Padding(
                padding: const EdgeInsets.all(12),
                child: SelectableText(
                  r.responseBody ?? r.errorMessage ?? '',
                  style: const TextStyle(fontFamily: 'monospace', fontSize: 11, color: Colors.white70),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _AuthTab extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final api = context.read<ApiClient>();
    final auth = context.watch<AuthProvider>();
    final profile = context.watch<ProfileProvider>();

    return FutureBuilder<String?>(
      future: api.getAccessToken(),
      builder: (context, snap) {
        final token = snap.data;
        final expiry = DebugUtils.jwtExpiry(token);
        final masked = token == null || token.isEmpty
            ? '—'
            : '${token.substring(0, token.length.clamp(0, 8))}…(${token.length} chars)';

        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _InfoRow('Logged in', '${auth.loggedIn}'),
            _InfoRow('App approved', '${auth.appApproved}'),
            _InfoRow('Partner name', auth.partnerName ?? profile.displayName),
            _InfoRow('Token', masked),
            _InfoRow('Access expiry', DebugUtils.expiryLabel(expiry)),
            _InfoRow('Refresh token', 'N/A (partner JWT only)'),
            const SizedBox(height: 16),
            const Text(
              'Token errors and auth logs appear in Errors tab with filter Auth.',
              style: TextStyle(color: Colors.white54, fontSize: 12),
            ),
          ],
        );
      },
    );
  }
}

class _DeviceTab extends StatelessWidget {
  const _DeviceTab({this.packageInfo});

  final PackageInfo? packageInfo;

  @override
  Widget build(BuildContext context) {
    final store = context.watch<DebugLogStore>();
    final route = store.currentRoute ?? GoRouter.of(context).state.uri.toString();
    final profile = context.watch<ProfileProvider>();

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _InfoRow('Screen / route', route),
        _InfoRow('User', profile.displayName),
        _InfoRow('API base', ApiConfig.baseUrl),
        _InfoRow('App version', packageInfo?.version ?? '…'),
        _InfoRow('Build', packageInfo?.buildNumber ?? '…'),
        _InfoRow('Package', packageInfo?.packageName ?? '…'),
        _InfoRow('Debug mode', '${DebugConfig.enabled}'),
        _InfoRow('Network', store.network.label),
        _InfoRow('Last network check', '${store.network.lastChecked}'),
      ],
    );
  }
}

class _RequestTile extends StatelessWidget {
  const _RequestTile(this.record);

  final ApiRequestRecord record;

  @override
  Widget build(BuildContext context) {
    final color = switch (record.status) {
      ApiRequestStatus.loading => Colors.amber,
      ApiRequestStatus.success => Colors.greenAccent,
      ApiRequestStatus.failure => Colors.redAccent,
    };

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      color: const Color(0xFF21262D),
      child: ExpansionTile(
        leading: Icon(
          record.status == ApiRequestStatus.loading ? Icons.hourglass_top : Icons.http,
          color: color,
          size: 20,
        ),
        title: Text(
          '${record.method} ${record.statusCode ?? "…"}',
          style: TextStyle(color: color, fontWeight: FontWeight.w600, fontSize: 13),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(record.url, style: const TextStyle(fontSize: 11, color: Colors.white54)),
            if (record.duration != null)
              Text(
                '${record.duration!.inMilliseconds} ms',
                style: const TextStyle(fontSize: 10, color: Colors.white38),
              ),
            if (record.isMultipart && record.uploadTotal != null)
              Text(
                'Upload ${record.uploadSent ?? 0}/${record.uploadTotal}',
                style: const TextStyle(fontSize: 10, color: Colors.white38),
              ),
          ],
        ),
        children: [
          _MonoBlock('Request headers', record.requestHeaders?.entries.map((e) => '${e.key}: ${e.value}').join('\n') ?? ''),
          _MonoBlock('Request body', record.requestBody ?? ''),
          _MonoBlock('Response', record.responseBody ?? record.errorMessage ?? ''),
        ],
      ),
    );
  }
}

class _LogTile extends StatelessWidget {
  const _LogTile(this.entry);

  final DebugLogEntry entry;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      color: const Color(0xFF21262D),
      child: ExpansionTile(
        title: Text(entry.title, style: const TextStyle(color: Colors.white, fontSize: 13)),
        subtitle: Text(
          '${entry.category.name} · ${entry.timestamp.toIso8601String()}',
          style: const TextStyle(fontSize: 10, color: Colors.white54),
        ),
        children: [
          if (entry.message != null) _MonoBlock('Message', entry.message!),
          if (entry.stackTrace != null) _MonoBlock('Stack', entry.stackTrace!),
        ],
      ),
    );
  }
}

class _MonoBlock extends StatelessWidget {
  const _MonoBlock(this.label, this.body);

  final String label;
  final String body;

  @override
  Widget build(BuildContext context) {
    if (body.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(color: Colors.tealAccent, fontSize: 11)),
          const SizedBox(height: 4),
          SelectableText(
            body,
            style: const TextStyle(fontFamily: 'monospace', fontSize: 11, color: Colors.white70),
          ),
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow(this.label, this.value);

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(label, style: const TextStyle(color: Colors.white54, fontSize: 12)),
          ),
          Expanded(
            child: SelectableText(
              value,
              style: const TextStyle(color: Colors.white, fontSize: 12),
            ),
          ),
        ],
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState(this.message);

  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Text(message, style: const TextStyle(color: Colors.white38)),
    );
  }
}
