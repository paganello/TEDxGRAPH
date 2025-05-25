import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:mytedx/data/models/talk.dart';
import 'package:mytedx/navigation/app_router.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:mytedx/presentation/providers/talk_providers.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  final _tagController = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  @override
  void dispose() {
    _tagController.dispose();
    super.dispose();
  }

  void _searchByTag() {
    if (_formKey.currentState!.validate()) {
      final tag = _tagController.text.trim();
      context.push('${AppRouter.talksByTagRoute}/$tag');
    }
  }

  void _searchByRandomTag() async {
    try {
      final talkApiService = ref.watch(talkApiServiceProvider);
      final randomTag = await talkApiService.getRandomTag();
      context.push('${AppRouter.talksByTagRoute}/$randomTag');
    } catch (e) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Error fetching random tag: $e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: const Text('TEDxGRAPH'),
        actions: [
          IconButton(
            icon: const Icon(Icons.search),
            tooltip: 'Global Search',
            onPressed: () {
              context.push(AppRouter.globalSearchRoute);
            },
          ),
        ],
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Form(
            key: _formKey,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                FaIcon(
                  FontAwesomeIcons.microphoneLines,
                  size: 80,
                  color: theme.colorScheme.primary,
                ),
                const SizedBox(height: 24),
                Text(
                  'Discover Inspiring Talks',
                  style: theme.textTheme.displayMedium,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 12),
                Text(
                  'Enter a tag to find TEDx talks that spark your curiosity.',
                  style: theme.textTheme.titleMedium,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 32),
                TextFormField(
                  controller: _tagController,
                  decoration: const InputDecoration(
                    labelText: 'Enter Tag (e.g., technology, innovation)',
                    hintText: 'Type a tag here',
                    prefixIcon: Icon(Icons.tag),
                  ),
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return 'Please enter a tag';
                    }
                    return null;
                  },
                  onFieldSubmitted: (_) => _searchByTag(),
                ),
                const SizedBox(height: 24),
                ElevatedButton.icon(
                  icon: const Icon(Icons.search_rounded),
                  label: const Text('Search by Tag'),
                  onPressed: _searchByTag,
                  style: theme.elevatedButtonTheme.style?.copyWith(
                    padding: MaterialStateProperty.all(
                      const EdgeInsets.symmetric(vertical: 16),
                    ),
                  ),
                ),
                const SizedBox(height: 32),
                Text('Talks you may like', style: theme.textTheme.titleLarge),
                const SizedBox(height: 12),

                ref
                    .watch(randomTagTalksProvider)
                    .when(
                      data: (data) {
                        final tag = data['tag'] as String;
                        final talks = data['talks'] as List<Talk>;

                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Tag: $tag',
                              style: theme.textTheme.labelLarge,
                            ),
                            const SizedBox(height: 12),
                            ListView.builder(
                              shrinkWrap: true,
                              physics: const NeverScrollableScrollPhysics(),
                              itemCount: talks.length > 8 ? 8 : talks.length,
                              itemBuilder: (context, index) {
                                final talk = talks[index];
                                return Card(
                                  child: ListTile(
                                    title: Text(talk.title),
                                    subtitle: Text(talk.mainSpeaker),
                                    onTap: () {
                                      // Naviga o mostra dettagli
                                    },
                                  ),
                                );
                              },
                            ),
                          ],
                        );
                      },
                      loading:
                          () =>
                              const Center(child: CircularProgressIndicator()),
                      error: (err, stack) => Text('Error loading talks: $err'),
                    ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
