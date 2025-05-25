import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mytedx/core/constants/api_constants.dart';
import 'package:mytedx/data/models/talk.dart';
import 'package:mytedx/data/models/related_talk.dart';
import 'package:mytedx/data/models/talk_summary.dart';
import 'package:mytedx/data/services/talk_api_service.dart';

// Provider per TalkApiService
final talkApiServiceProvider = Provider<TalkApiService>(
  (ref) => TalkApiService(),
);

final randomTagTalksProvider = FutureProvider.autoDispose((ref) async {
  final api = ref.watch(talkApiServiceProvider);
  final tag = await api.getRandomTag();
  final talks = await api.getTalksByTag(tag, 1);
  return {'tag': tag, 'talks': talks};
});

// Provider per la lista dei talk per tag (con paginazione)
final talksByTagProvider = StateNotifierProvider.family<
  TalksByTagNotifier,
  AsyncValue<List<Talk>>,
  String
>((ref, tag) {
  return TalksByTagNotifier(ref.watch(talkApiServiceProvider), tag);
});

class TalksByTagNotifier extends StateNotifier<AsyncValue<List<Talk>>> {
  final TalkApiService _apiService;
  final String _tag;
  int _currentPage = 1;
  bool _isLoadingMore = false;
  bool _hasMore = true;

  TalksByTagNotifier(this._apiService, this._tag)
    : super(const AsyncValue.loading()) {
    fetchInitialTalks();
  }

  Future<void> fetchInitialTalks() async {
    _currentPage = 1;
    _hasMore = true;
    state = const AsyncValue.loading();
    try {
      final talks = await _apiService.getTalksByTag(_tag, _currentPage);
      if (talks.isEmpty || talks.length < ApiConstants.talksPerPage) {
        _hasMore = false;
      }
      state = AsyncValue.data(talks);
    } catch (e, s) {
      state = AsyncValue.error(e, s);
    }
  }

  Future<void> fetchMoreTalks() async {
    if (_isLoadingMore ||
        !_hasMore ||
        state is AsyncLoading ||
        state is AsyncError)
      return;

    _isLoadingMore = true;
    // Non reimpostare lo stato su loading qui per mantenere i dati esistenti visibili

    try {
      _currentPage++;
      final newTalks = await _apiService.getTalksByTag(_tag, _currentPage);
      if (newTalks.isEmpty || newTalks.length < ApiConstants.talksPerPage) {
        _hasMore = false;
      }
      state = AsyncValue.data([...(state.value ?? []), ...newTalks]);
    } catch (e, s) {
      // In caso di errore nel caricare "di più", potresti voler gestire diversamente
      // Ad esempio, tornare alla pagina precedente o mostrare un errore temporaneo
      _currentPage--; // rollback page
      // Per semplicità, non cambiamo lo stato qui, ma logghiamo l'errore
      print("Error fetching more talks: $e");
    } finally {
      _isLoadingMore = false;
    }
  }

  bool get hasMoreData => _hasMore;
  bool get isLoadingMoreData => _isLoadingMore;
}

// Provider per i dettagli di un talk (usato nella TalkDetailScreen)
final talkDetailProvider = FutureProvider.family<Talk, String>((
  ref,
  talkId,
) async {
  // Questo provider dovrebbe recuperare un singolo talk completo se necessario.
  // Se la lista dei talk by tag contiene già tutti i dati, si può passare l'oggetto Talk.
  // Se invece l'API Get_Talks_By_ID restituisce solo un sottoinsieme di dati e
  // c'è un'altra API per ottenere il dettaglio completo di un talk (non fornita),
  // allora questa andrebbe chiamata qui.
  // Per ora, assumiamo che l'oggetto Talk passato come argomento a TalkDetailScreen
  // sia sufficiente, quindi questo provider potrebbe non essere strettamente necessario
  // per il Talk base. Lo manteniamo per coerenza se in futuro si aggiungesse un fetch specifico.
  // Oppure, se non abbiamo l'oggetto Talk completo, potremmo cercare di ottenerlo.
  // L'approccio più semplice: la TalkDetailScreen riceve un oggetto Talk.
  // Quindi, questo provider non serve per il Talk base in sé, ma per i suoi dati correlati.

  // In questo esempio, questo provider non caricherà il talk base, ma è un placeholder.
  // La TalkDetailScreen riceverà l'oggetto Talk via `extra` di GoRouter.
  // Se invece volessi recuperare il Talk da un'API basata sull'ID:
  // return ref.watch(talkApiServiceProvider).getTalkById(talkId);
  throw UnimplementedError(
    "talkDetailProvider should fetch a full talk if not passed via arguments.",
  );
});

// Provider per il riassunto del talk
final talkSummaryProvider = FutureProvider.family<TalkSummary, String>((
  ref,
  talkId,
) {
  return ref.watch(talkApiServiceProvider).getTalkSummary(talkId);
});

// Provider per i talk correlati
final relatedTalksProvider = FutureProvider.family<List<RelatedTalk>, String>((
  ref,
  talkId,
) {
  return ref.watch(talkApiServiceProvider).getRelatedTalks(talkId);
});
