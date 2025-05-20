import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mytedx/data/models/searched_talk.dart';
import 'package:mytedx/data/services/talk_api_service.dart';
import 'package:mytedx/presentation/providers/talk_providers.dart'; // per talkApiServiceProvider

final globalSearchQueryProvider = StateProvider<String>((ref) => '');

final globalSearchResultsProvider = FutureProvider<List<SearchedTalk>>((
  ref,
) async {
  final query = ref.watch(globalSearchQueryProvider);
  if (query.trim().isEmpty || query.trim().length < 3) {
    // Non cercare se query troppo corta
    return [];
  }
  return ref.watch(talkApiServiceProvider).searchTalksByTitle(query);
});
