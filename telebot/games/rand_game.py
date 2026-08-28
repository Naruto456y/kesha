import random
import time

class NumberGuessingGame:
    def __init__(self):
        self.score = 0
        self.games_played = 0
        
    def display_welcome(self):
        print("=" * 50)
        print("🎮 ДОБРО ПОЖАЛОВАТЬ В ИГРУ 'УГАДАЙ ЧИСЛО' 🎮")
        print("=" * 50)
        print("Правила игры:")
        print("• Компьютер загадывает число")
        print("• Вы пытаетесь его угадать")
        print("• За каждую попытку снимаются очки")
        print("• Чем быстрее угадаете, тем больше очков!")
        print("=" * 50)
    
    def choose_difficulty(self):
        print("\nВыберите уровень сложности:")
        print("1. Легкий (1-50, 10 попыток)")
        print("2. Средний (1-100, 8 попыток)")
        print("3. Сложный (1-200, 6 попыток)")
        print("4. Экстремальный (1-500, 5 попыток)")
        
        while True:
            try:
                choice = int(input("\nВаш выбор (1-4): "))
                if choice == 1:
                    return 50, 10, 100
                elif choice == 2:
                    return 100, 8, 150
                elif choice == 3:
                    return 200, 6, 200
                elif choice == 4:
                    return 500, 5, 300
                else:
                    print("Пожалуйста, выберите число от 1 до 4!")
            except ValueError:
                print("Пожалуйста, введите корректное число!")
    
    def play_round(self):
        max_num, max_attempts, base_score = self.choose_difficulty()
        secret_number = random.randint(1, max_num)
        attempts = 0
        
        print(f"\n🎯 Я загадал число от 1 до {max_num}")
        print(f"У вас есть {max_attempts} попыток!")
        print(f"Максимальный балл за эту игру: {base_score}")
        
        start_time = time.time()
        
        while attempts < max_attempts:
            try:
                attempts += 1
                guess = int(input(f"\nПопытка {attempts}/{max_attempts}. Ваше число: "))
                
                if guess == secret_number:
                    end_time = time.time()
                    time_taken = round(end_time - start_time, 1)
                    
                    # Подсчет очков
                    remaining_attempts = max_attempts - attempts + 1
                    time_bonus = max(0, 30 - int(time_taken))
                    round_score = base_score + (remaining_attempts * 10) + time_bonus
                    
                    print(f"\n🎉 ПОЗДРАВЛЯЮ! Вы угадали число {secret_number}!")
                    print(f"⏱️  Время: {time_taken} секунд")
                    print(f"🎯 Попыток использовано: {attempts}")
                    print(f"⭐ Очки за раунд: {round_score}")
                    
                    self.score += round_score
                    self.games_played += 1
                    return True
                    
                elif guess < secret_number:
                    remaining = max_attempts - attempts
                    if remaining > 0:
                        print(f"📈 Загаданное число БОЛЬШЕ! Осталось попыток: {remaining}")
                    
                elif guess > secret_number:
                    remaining = max_attempts - attempts
                    if remaining > 0:
                        print(f"📉 Загаданное число МЕНЬШЕ! Осталось попыток: {remaining}")
                        
            except ValueError:
                print("❌ Пожалуйста, введите корректное число!")
                attempts -= 1  # Не засчитываем неправильный ввод
        
        print(f"\n💔 Попытки закончились! Загаданное число было: {secret_number}")
        self.games_played += 1
        return False
    
    def show_statistics(self):
        if self.games_played > 0:
            win_rate = (self.score > 0) * 100 // self.games_played if self.games_played > 0 else 0
            print(f"\n📊 СТАТИСТИКА:")
            print(f"🎮 Игр сыграно: {self.games_played}")
            print(f"⭐ Общий счет: {self.score}")
            print(f"📈 Средний балл: {self.score // self.games_played if self.games_played > 0 else 0}")
        else:
            print("\n📊 Статистика пуста. Сыграйте хотя бы одну игру!")
    
    def main_menu(self):
        self.display_welcome()
        
        while True:
            print(f"\n🏆 Текущий счет: {self.score}")
            print("\n--- ГЛАВНОЕ МЕНЮ ---")
            print("1. 🎮 Играть")
            print("2. 📊 Статистика")
            print("3. 🏆 Рекорды")
            print("4. ❌ Выход")
            
            try:
                choice = int(input("\nВыберите действие (1-4): "))
                
                if choice == 1:
                    print("\n" + "="*30)
                    result = self.play_round()
                    if result:
                        print("🎊 Отличная игра!")
                    else:
                        print("😔 Не расстраивайтесь, попробуйте еще раз!")
                    print("="*30)
                    
                elif choice == 2:
                    self.show_statistics()
                    
                elif choice == 3:
                    self.show_records()
                    
                elif choice == 4:
                    print("\n👋 Спасибо за игру! До свидания!")
                    if self.games_played > 0:
                        print(f"🏆 Ваш финальный счет: {self.score}")
                    break
                    
                else:
                    print("❌ Пожалуйста, выберите число от 1 до 4!")
                    
            except ValueError:
                print("❌ Пожалуйста, введите корректное число!")
    
    def show_records(self):
        records = [
            ("🥉 Новичок", 100),
            ("🥈 Любитель", 500),
            ("🥇 Эксперт", 1000),
            ("🏆 Мастер", 2000),
            ("👑 Легенда", 5000)
        ]
        
        print("\n🏆 ТАБЛИЦА РЕКОРДОВ:")
        print("-" * 30)
        
        current_rank = "🔰 Начинающий"
        for rank, required_score in records:
            status = "✅" if self.score >= required_score else "❌"
            print(f"{status} {rank}: {required_score} очков")
            if self.score >= required_score:
                current_rank = rank
        
        print(f"\n🎖️  Ваш текущий ранг: {current_rank}")
        print(f"⭐ Ваш счет: {self.score}")

# Запуск игры
def game():
    game = NumberGuessingGame()
    game.main_menu()
if __name__ == "__main__":
    game()