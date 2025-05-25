import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mytedx/core/utils/debouncer.dart';
import 'package:mytedx/presentation/providers/search_providers.dart';
import 'package:mytedx/presentation/widgets/common_widgets.dart';
import 'package:mytedx/navigation/app_router.dart'; // Per navigare al dettaglio
import 'package:go_router/go_router.dart';
import 'package:mytedx/data/models/talk.dart'; // Per passare un oggetto Talk parziale

class GlobalSearchScreen extends ConsumerStatefulWidget {
  const GlobalSearchScreen({super.key});

  @override
  ConsumerState<GlobalSearchScreen> createState() => _GlobalSearchScreenState();
}

class _GlobalSearchScreenState extends ConsumerState<GlobalSearchScreen> {
  final _searchController = TextEditingController();
  final _debouncer = Debouncer(milliseconds: 500);

  @override
  void initState() {
    super.initState();
    // Imposta il controller con il valore attuale del provider (se l'utente torna indietro)
    _searchController.text = ref.read(globalSearchQueryProvider);
    _searchController.addListener(() {
      _debouncer.run(() {
        if (mounted) {
          // Assicura che il widget sia ancora montato
          ref.read(globalSearchQueryProvider.notifier).state =
              _searchController.text;
        }
      });
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    _debouncer.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final searchResultsAsync = ref.watch(globalSearchResultsProvider);
    final currentQuery = ref.watch(globalSearchQueryProvider);
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(title: const Text('Search Talks by Title')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: TextField(
              controller: _searchController,
              autofocus: true,
              decoration: InputDecoration(
                hintText: 'Enter talk title...',
                prefixIcon: const Icon(Icons.search),
                suffixIcon:
                    _searchController.text.isNotEmpty
                        ? IconButton(
                          icon: const Icon(Icons.clear),
                          onPressed: () {
                            _searchController.clear();
                            ref.read(globalSearchQueryProvider.notifier).state =
                                '';
                          },
                        )
                        : null,
              ),
            ),
          ),
          Expanded(
            child:
                (currentQuery.trim().isEmpty || currentQuery.trim().length < 3)
                    ? const EmptyContent(
                      message: 'Enter at least 3 characters to search.',
                      icon: Icons.search_off_outlined,
                    )
                    : searchResultsAsync.when(
                      data: (results) {
                        if (results.isEmpty) {
                          return EmptyContent(
                            message:
                                'No talks found for "${_searchController.text}".',
                          );
                        }
                        return ListView.builder(
                          itemCount: results.length,
                          itemBuilder: (context, index) {
                            final searchedTalk = results[index];
                            return ListTile(
                              leading: Icon(
                                Icons.play_circle_outline,
                                color: theme.colorScheme.primary,
                              ),
                              title: Text(searchedTalk.title),
                              onTap: () {
                                // Per navigare al dettaglio, abbiamo bisogno di un oggetto Talk.
                                // L'API di ricerca restituisce solo id e titolo.
                                // Opzione 1: Creare un oggetto Talk "parziale" e sperare che la
                                //            TalkDetailScreen gestisca i campi mancanti o li carichi.
                                // Opzione 2: Avere un provider in TalkDetailScreen che carica
                                //            il talk completo dato l'ID. (Preferibile)
                                // Per ora, implementiamo l'opzione 1 come placeholder.
                                // Idealmente, Get_Talks_By_ID dovrebbe essere in grado di
                                // recuperare un talk anche tramite il suo ID.
                                // Oppure, la lambda Search_Nodes_By_Title_Neo4j dovrebbe restituire più dati.

                                // Creiamo un Talk minimale. La TalkDetailScreen poi caricherà
                                // il riassunto e i related talks basandosi su searchedTalk.id
                                final partialTalk = Talk(
                                  id: searchedTalk.id,
                                  title: searchedTalk.title,
                                  details: searchedTalk.details, // Placeholder
                                  slug:
                                      searchedTalk
                                          .id, // Usa id come slug se non disponibile altrimenti
                                  mainSpeaker:
                                      searchedTalk.mainSpeaker,
                                  url: '',
                                );
                                context.push(
                                  '${AppRouter.talkDetailRoute}/${searchedTalk.id}',
                                  extra: partialTalk,
                                );
                              },
                            );
                          },
                        );
                      },
                      loading: () => const AppLoader(),
                      error:
                          (error, stack) => ErrorDisplay(
                            message: error.toString(),
                            onRetry: () {
                              // Forzare un refresh invalidando il provider o ritentando la query
                              ref.invalidate(globalSearchResultsProvider);
                            },
                          ),
                    ),
          ),
        ],
      ),
    );
  }
}
