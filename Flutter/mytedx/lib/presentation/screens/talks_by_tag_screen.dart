import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mytedx/presentation/providers/talk_providers.dart';
import 'package:mytedx/presentation/widgets/talk_card.dart';
import 'package:mytedx/presentation/widgets/common_widgets.dart';

class TalksByTagScreen extends ConsumerStatefulWidget {
  final String tag;
  const TalksByTagScreen({super.key, required this.tag});

  @override
  ConsumerState<TalksByTagScreen> createState() => _TalksByTagScreenState();
}

class _TalksByTagScreenState extends ConsumerState<TalksByTagScreen> {
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 200) {
      // Se non ci sono più dati o si sta già caricando, non fare nulla
      final notifier = ref.read(talksByTagProvider(widget.tag).notifier);
      if (notifier.hasMoreData && !notifier.isLoadingMoreData) {
        notifier.fetchMoreTalks();
      }
    }
  }

  @override
  void dispose() {
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final talksAsyncValue = ref.watch(talksByTagProvider(widget.tag));
    final talksNotifier = ref.watch(talksByTagProvider(widget.tag).notifier);

    return Scaffold(
      appBar: AppBar(title: Text('Talks for #${widget.tag}')),
      body: talksAsyncValue.when(
        data: (talks) {
          if (talks.isEmpty) {
            return EmptyContent(
              message: 'No talks found for the tag "${widget.tag}".',
            );
          }
          return RefreshIndicator(
            onRefresh:
                () =>
                    ref
                        .read(talksByTagProvider(widget.tag).notifier)
                        .fetchInitialTalks(),
            child: ListView.builder(
              controller: _scrollController,
              itemCount: talks.length + (talksNotifier.hasMoreData ? 1 : 0),
              itemBuilder: (context, index) {
                if (index == talks.length && talksNotifier.hasMoreData) {
                  return const Padding(
                    padding: EdgeInsets.symmetric(vertical: 16.0),
                    child: AppLoader(size: 30),
                  );
                }
                if (index >= talks.length)
                  return const SizedBox.shrink(); // safety
                return TalkCard(talk: talks[index]);
              },
            ),
          );
        },
        loading: () => const AppLoader(),
        error:
            (error, stackTrace) => ErrorDisplay(
              message: error.toString(),
              onRetry:
                  () =>
                      ref
                          .read(talksByTagProvider(widget.tag).notifier)
                          .fetchInitialTalks(),
            ),
      ),
    );
  }
}
