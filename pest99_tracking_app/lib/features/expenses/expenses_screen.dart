import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../providers/operations_provider.dart';
import '../../shared/widgets/section_header.dart';

class ExpensesScreen extends StatefulWidget {
  const ExpensesScreen({super.key});

  @override
  State<ExpensesScreen> createState() => _ExpensesScreenState();
}

class _ExpensesScreenState extends State<ExpensesScreen> {
  int? _categoryId;
  final _amount = TextEditingController();
  final _description = TextEditingController();
  bool _useGps = false;

  @override
  void initState() {
    super.initState();
    Future<void>(() => context.read<OperationsProvider>().loadExpenses());
  }

  @override
  void dispose() {
    _amount.dispose();
    _description.dispose();
    super.dispose();
  }

  Color _statusColor(String? status) {
    switch (status) {
      case 'approved':
        return AppColors.successText;
      case 'rejected':
        return AppColors.danger;
      default:
        return AppColors.warning;
    }
  }

  @override
  Widget build(BuildContext context) {
    final ops = context.watch<OperationsProvider>();

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(title: const Text('Expenses')),
      body: RefreshIndicator(
        onRefresh: ops.loadExpenses,
        color: AppColors.primary,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.screenEdge),
          children: [
            const SectionHeader('New claim'),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(AppSpacing.cardPadding),
                child: Column(
                  children: [
                    DropdownButtonFormField<int>(
                      initialValue: _categoryId,
                      decoration: const InputDecoration(labelText: 'Category'),
                      items: [
                        for (final c in ops.expenseCategories)
                          DropdownMenuItem(value: c['id'] as int, child: Text(c['name']?.toString() ?? '')),
                      ],
                      onChanged: (v) => setState(() => _categoryId = v),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _amount,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(labelText: 'Amount (₹)', prefixIcon: Icon(Icons.currency_rupee)),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _description,
                      decoration: const InputDecoration(labelText: 'Description'),
                    ),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Auto-calculate travel from today GPS distance'),
                      value: _useGps,
                      activeThumbColor: AppColors.primary,
                      onChanged: (v) => setState(() => _useGps = v),
                    ),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton(
                        onPressed: _categoryId == null || (!_useGps && _amount.text.isEmpty)
                            ? null
                            : () async {
                                final ok = await ops.submitExpense(
                                  categoryId: _categoryId!,
                                  date: DateTime.now().toString().substring(0, 10),
                                  amount: _amount.text.isEmpty ? '0' : _amount.text,
                                  description: _description.text,
                                  useGps: _useGps,
                                );
                                if (ok && mounted) {
                                  ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Expense submitted')));
                                  _amount.clear();
                                  _description.clear();
                                }
                              },
                        child: const Text('Submit claim'),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: AppSpacing.sectionGap),
            const SectionHeader('My claims'),
            ...ops.expenses.map(
              (e) => Card(
                child: ListTile(
                  leading: Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: AppColors.successBg,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.receipt_long, color: AppColors.primary, size: 20),
                  ),
                  title: Text('${e['category_name']} — ₹${e['amount']}'),
                  subtitle: Text('${e['expense_date']} • ${e['status']}'),
                  trailing: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: _statusColor(e['status']?.toString()).withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          e['status']?.toString() ?? '',
                          style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: _statusColor(e['status']?.toString())),
                        ),
                      ),
                      if (e['status'] == 'pending')
                        IconButton(
                          icon: const Icon(Icons.camera_alt_outlined, color: AppColors.primary),
                          onPressed: () => _uploadReceipt(context, e['id'] as int),
                        ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  Future<void> _uploadReceipt(BuildContext context, int claimId) async {
    final picker = ImagePicker();
    final file = await picker.pickImage(source: ImageSource.camera, imageQuality: 80);
    if (file == null) return;
    try {
      await context.read<OperationsProvider>().uploadReceipt(claimId, file.path);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Receipt uploaded')));
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
      }
    }
  }
}
