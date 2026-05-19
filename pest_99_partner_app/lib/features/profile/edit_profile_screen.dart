import 'dart:io';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../providers/profile_provider.dart';
import '../../shared/widgets/app_text_field.dart';
import '../../shared/widgets/primary_button.dart';

class EditProfileScreen extends StatefulWidget {
  const EditProfileScreen({super.key});

  @override
  State<EditProfileScreen> createState() => _EditProfileScreenState();
}

ImageProvider? _avatarImage(String? pickedPath, String? url) {
  if (pickedPath != null && pickedPath.isNotEmpty) {
    return FileImage(File(pickedPath));
  }
  if (url != null && url.isNotEmpty) {
    return NetworkImage(url);
  }
  return null;
}

class _EditProfileScreenState extends State<EditProfileScreen> {
  final _nameController = TextEditingController();
  final _mobileController = TextEditingController();
  String? _pickedImagePath;
  bool _initialized = false;

  @override
  void dispose() {
    _nameController.dispose();
    _mobileController.dispose();
    super.dispose();
  }

  void _bindFromProvider(ProfileProvider profile) {
    if (_initialized || profile.profile == null) return;
    final p = profile.profile!;
    _nameController.text = p.fullName;
    _mobileController.text = p.mobile;
    _initialized = true;
  }

  Future<void> _pickImage() async {
    final picker = ImagePicker();
    final file = await picker.pickImage(
      source: ImageSource.gallery,
      maxWidth: 1200,
      imageQuality: 85,
    );
    if (file != null && mounted) {
      setState(() => _pickedImagePath = file.path);
    }
  }

  Future<void> _save() async {
    final name = _nameController.text.trim();
    if (name.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter your full name')),
      );
      return;
    }

    final provider = context.read<ProfileProvider>();
    final ok = await provider.updateProfile(
      fullName: name,
      imagePath: _pickedImagePath,
    );
    if (!mounted) return;
    if (ok) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Profile updated')),
      );
      context.pop();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(provider.error ?? 'Could not save profile')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final profile = context.watch<ProfileProvider>();
    _bindFromProvider(profile);

    final avatarUrl = profile.profile?.profileImageUrl;
    final saving = profile.loading;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Edit Profile'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(AppSpacing.screenEdge),
        children: [
          Center(
            child: GestureDetector(
              onTap: _pickImage,
              child: Stack(
                children: [
                  CircleAvatar(
                    radius: 52,
                    backgroundColor: AppColors.surfaceContainerHigh,
                    backgroundImage: _avatarImage(_pickedImagePath, avatarUrl),
                    child: _pickedImagePath == null &&
                            (avatarUrl == null || avatarUrl.isEmpty)
                        ? const Icon(Icons.person, size: 48)
                        : null,
                  ),
                  Positioned(
                    right: 0,
                    bottom: 0,
                    child: Container(
                      padding: const EdgeInsets.all(6),
                      decoration: const BoxDecoration(
                        color: AppColors.primary,
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.camera_alt, size: 18, color: Colors.white),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),
          Center(
            child: Text(
              'Tap to change photo',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: AppColors.textSecondary,
                  ),
            ),
          ),
          const SizedBox(height: AppSpacing.sectionGap),
          AppTextField(
            label: 'Full name',
            hint: 'Your name',
            controller: _nameController,
          ),
          const SizedBox(height: AppSpacing.sectionGap),
          Text(
            'Mobile number',
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
          ),
          const SizedBox(height: 8),
          TextFormField(
            controller: _mobileController,
            readOnly: true,
            decoration: InputDecoration(
              hintText: 'Registered mobile',
              filled: true,
              fillColor: AppColors.surfaceContainerHigh,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
            ),
          ),
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text(
              'Mobile is linked to your login and cannot be changed here.',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: AppColors.textSecondary,
                  ),
            ),
          ),
          const SizedBox(height: AppSpacing.sectionGap),
          PrimaryButton(
            label: saving ? 'Saving…' : 'Save Changes',
            onPressed: saving ? null : _save,
          ),
        ],
      ),
    );
  }
}
