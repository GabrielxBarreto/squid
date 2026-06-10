from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from .models import Streaming

class StreamingListView(ListView):
    model = Streaming
    template_name = 'streaming/streaming_list.html'
    context_object_name = 'streamings'

class StreamingCreateView(CreateView):
    model = Streaming
    template_name = 'streaming/streaming_form.html'
    fields = ['nome', 'preco_total', 'max_membros', 'descricao']
    success_url = reverse_lazy('streaming:lista')

class StreamingUpdateView(UpdateView):
    model = Streaming
    template_name = 'streaming/streaming_form.html'
    fields = ['nome', 'preco_total', 'max_membros', 'descricao']
    success_url = reverse_lazy('streaming:lista')

class StreamingDeleteView(DeleteView):
    model = Streaming
    template_name = 'streaming/streaming_confirm_delete.html'
    success_url = reverse_lazy('streaming:lista')