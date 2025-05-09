import { Injectable, signal } from '@angular/core';
import { Todo } from '../models/model/todo.model';
import { TodoKeyLocalStorage } from '../models/enum/todoKeyLocalStorage';

@Injectable({
  providedIn: 'root'
})
export class TodoSignalsService {

  constructor() { }

  public todosState = signal<Array<Todo>>([]);

  public updateTodos({ id, title, description, done }: Todo): void {
    if ((title && id && description !== null) || undefined) {
      const updatedTodos = [...this.todosState(), new Todo(id, title, description, done)];
      this.todosState.set(updatedTodos);
      this.saveTodosInLocalStorage();
    }
  }

  public saveTodosInLocalStorage(): void {
    const todos = JSON.stringify(this.todosState());
    if (typeof localStorage !== 'undefined' && todos) {
      localStorage.setItem(TodoKeyLocalStorage.TODO_LIST, todos);
    }
  }

}
